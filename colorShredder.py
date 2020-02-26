import png
import numpy

from numba import njit

import os
import sys
import concurrent.futures
import time

import colorTools
import canvasTools
import config

# =============================================================================
# MACROS
# =============================================================================
FILENAME = "painting"

MODE = config.mode['CURRENT']

SHUFFLE_COLORS = config.color['SHUFFLE']
USE_MULTIPROCESSING = config.color['SHUFFLE']

PRINT_RATE = config.painter['PRINT_RATE']
LOCATIONS_PER_PAINTER = config.painter['LOCATIONS_PER_PAINTER']
MIN_MULTI_WORKLOAD = config.painter['MIN_MULTI_WORKLOAD']
MAX_PAINTERS = os.cpu_count() * 2

COLOR_BIT_DEPTH = config.canvas['COLOR_BIT_DEPTH']
CANVAS_SIZE = (config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT'])
START_POINT = (config.canvas['START_X'], config.canvas['START_Y'])

BLACK = numpy.array([0, 0, 0], numpy.uint32)
INVALID_COORD = (-1, -1)

# =============================================================================
# GLOBALS
# =============================================================================

# position in and the list of all colors to be placed
colorIndex = 0
colorCount = ((2**COLOR_BIT_DEPTH)**3)
allColors = numpy.zeros([colorCount, 3], numpy.uint32)

# used for ongoing speed calculation
lastPrintTime = time.time()

# tracked for informational printout / progress report
collisionCount = 0
coloredCount = 0

# dictionary used for lookup of coordinate_available locations
isAvailable = []

# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)
availabilityCanvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.bool)

# writes data arrays as PNG image files
pngWriter = png.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

# =============================================================================


def main():
    # Global Access
    global allColors

    # Setup
    allColors = colorTools.generateColors(
        COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    beginTime = time.time()
    paintCanvas()
    elapsedTime = time.time() - beginTime

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " +
          "{:3.2f}".format(elapsedTime / 60) + " minutes!")


# manages painting of the canvas
def paintCanvas():

    # draw the first color at the starting pixel
    startPainting()

    # while more un-colored boundry locations exist and there are more colors to be placed, continue painting
    while(isAvailable and (colorIndex < allColors.shape[0])):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    # Setup
    targetColor = allColors[colorIndex]

    # draw the first color at the starting pixel
    workingCanvas[START_POINT[0], START_POINT[1]] = targetColor
    colorIndex += 1

    filteredNeighbors = canvasTools.removeColoredNeighbors2(START_POINT, workingCanvas)

    # add its neigbors to isAvailable
    for neighbor in filteredNeighbors:
        if (not availabilityCanvas[neighbor]):
            isAvailable.append(neighbor)
            availabilityCanvas[neighbor] = True



    # finish first pixel
    coloredCount = 1
    printCurrentCanvas(True)


# continue the painting
def continuePainting():

    # Global Access
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    # Setup
    availableCount = len(isAvailable)

    # if more than MIN_MULTI_WORKLOAD locations are coordinate_available, allow multiprocessing
    if ((availableCount > MIN_MULTI_WORKLOAD) and USE_MULTIPROCESSING):
        painterManager = concurrent.futures.ProcessPoolExecutor()
        painters = []

        # cap the number of workers so that there are at least LOCATIONS_PER_PAINTER free locations per worker
        # this keeps the number of collisions down
        # loop over each one
        for _ in range(min(((availableCount//LOCATIONS_PER_PAINTER), MAX_PAINTERS))):

            if(len(allColors) > colorIndex):
                # get the color to be placed
                targetColor = allColors[colorIndex]
                colorIndex += 1

                # schedule a worker to find the best location for that color
                neighborDifferences = numpy.zeros(8, numpy.uint32)
                painters.append(painterManager.submit(
                    getBestPositionForColor, targetColor, neighborDifferences))

        # as each worker completes
        for painter in concurrent.futures.as_completed(painters):

            # collect the best location for that color
            workerResult = painter.result()
            workerTargetColor = workerResult[0]
            workerMinCoord = workerResult[1]

            # attempt to paint the color at the corresponding location
            paintToCanvas(workerTargetColor, workerMinCoord)

        # teardown the process pool
        painterManager.shutdown()

    # otherwise, use only the main process
    # This is because the overhead of multithreading makes singlethreading better for small problems
    else:
        # get the color to be placed
        targetColor = allColors[colorIndex]
        colorIndex += 1

        # find the best location for that color
        neighborDifferences = numpy.zeros(8, numpy.uint32)
        bestResult = getBestPositionForColor(targetColor, neighborDifferences)
        resultColor = bestResult[0]
        resultCoord = bestResult[1]

        # attempt to paint the color at the corresponding location
        paintToCanvas(resultColor, resultCoord)


# Gives the best location among all avilable for the requested color; Also returns the color itself
# # In other words, checks every coordinate_available location using considerPixelAt(), keeping track of the
# # minimum (best/closest) value returned and the location associated with it, this location "MinCoord"
# # is where we will place the target color
# @njit
def getBestPositionForColor(requestedColor, neighborDifferences):

    # reset minimums
    MinCoord = INVALID_COORD
    minDistance = sys.maxsize

    # for every coordinate_available position in the boundry, perform the check, keep the best position:
    for coordinate_available in isAvailable:

        # check = canvasTools.considerPixelAt(
        #     workingCanvas, coordinate_available, requestedColor, MODE)
        # def minimumSelection(workingCanvas, coordinate_available, requestedColor):

        index = 0
        neighborDifferences.fill(0)

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                neighbor = ((coordinate_available[0] - 1 + i), (coordinate_available[1] - 1 + j))

                # neighbor must be in the canvas
                neighborIsInCanvas = ((0 <= neighbor[0] < workingCanvas.shape[0])
                                    and (0 <= neighbor[1] < workingCanvas.shape[1]))

                if (neighborIsInCanvas):

                    neighborNotBlack = not numpy.array_equal(workingCanvas[neighbor[0], neighbor[1]], BLACK)
                    if (neighborNotBlack):

                        # get colDiff between the neighbor and target colors, add it to the list
                        neigborColor = workingCanvas[neighbor[0], neighbor[1]]

                        # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                        colorDifference = numpy.subtract(requestedColor, neigborColor)
                        differenceSquared = numpy.multiply(colorDifference, colorDifference)
                        squaresSum = numpy.sum(differenceSquared)
                        euclidianDistanceAprox = squaresSum

                        neighborDifferences[index] = euclidianDistanceAprox
                        index += 1

        if (MODE == 0):
            # check if the considered pixel has at least one valid neighbor
            if (index):
                # return the minimum difference of all the neighbors
                check = numpy.min(neighborDifferences)
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize
        
        if (MODE == 1):
            # check if the considered pixel has at least one valid neighbor
            if (index):
                # return the minimum difference of all the neighbors
                check = numpy.mean(neighborDifferences)
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            MinCoord = coordinate_available

    return (requestedColor, MinCoord)


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requestedCoord):

    # Global Access
    global collisionCount
    global coloredCount
    global isAvailable
    global workingCanvas

    # double check the the pixel is BLACK
    isBlack = numpy.array_equal(workingCanvas[requestedCoord[0], requestedCoord[1]], BLACK)
    if (isBlack):

        # the best position for requestedColor has been found color it
        workingCanvas[requestedCoord[0], requestedCoord[1]] = requestedColor

        # remove that position from isAvailable and increment the count
        isAvailable.remove(requestedCoord)
        availabilityCanvas[requestedCoord] = False
        
        coloredCount += 1

        filteredNeighbors = canvasTools.removeColoredNeighbors2(requestedCoord, workingCanvas)

        # add its neigbors to isAvailable
        for neighbor in filteredNeighbors:
            
            if (not availabilityCanvas[neighbor]):
                isAvailable.append(neighbor)
                availabilityCanvas[neighbor] = True


    # collision
    else:
        collisionCount += 1

    # print progress
    if (coloredCount % PRINT_RATE == 0):
        printCurrentCanvas()


# prints the current state of workingCanvas as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global lastPrintTime

    # get elapsed time
    currentTime = time.time()
    elapsed = currentTime - lastPrintTime

    # exclude duplicate printings
    if (elapsed > 0):
        rate = PRINT_RATE/elapsed

        # cancel (probably a duplicate)
        if (rate > 500) and not (finalize):
            return

        # write the png file
        name = (FILENAME + '.png')
        myFile = open(name, 'wb')
        pngWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
        myFile.close()

        # Info Print
        lastPrintTime = currentTime
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            coloredCount, len(isAvailable), (coloredCount * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), collisionCount, rate), end='\n')
        
    

if __name__ == '__main__':
    main()
