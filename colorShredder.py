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
CANVAS_SIZE = numpy.array(
    [config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT']], numpy.uint32)
START_POINT = numpy.array(
    [config.canvas['START_X'], config.canvas['START_Y']], numpy.uint32)

BLACK = numpy.array([0, 0, 0], numpy.uint32)
INVALID_COORD = numpy.array([-1, -1], numpy.int8)

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

# dictionary used for lookup of available locations
isAvailable = []

# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

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
    startPoint = numpy.array([START_POINT[0], START_POINT[1]], numpy.uint32)
    targetColor = allColors[colorIndex]

    # draw the first color at the starting pixel
    workingCanvas[startPoint[0], startPoint[1]] = targetColor
    colorIndex += 1

    # add its neigbors to isAvailable
    for neighbor in canvasTools.removeColoredNeighbors(canvasTools.getNeighbors(workingCanvas, startPoint), workingCanvas):
        isAvailable.append(neighbor)

    # finish first pixel
    coloredCount = 10
    printCurrentCanvas()


# continue the painting
def continuePainting():

    # Global Access
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    # Setup
    availableCount = len(isAvailable)

    # if more than MIN_MULTI_WORKLOAD locations are available, allow multiprocessing
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
                painters.append(painterManager.submit(
                    getBestPositionForColor, targetColor))

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
        bestResult = getBestPositionForColor(targetColor)
        resultColor = bestResult[0]
        resultCoord = bestResult[1]

        # attempt to paint the color at the corresponding location
        paintToCanvas(resultColor, resultCoord)


# Gives the best location among all avilable for the requested color; Also returns the color itself
# # In other words, checks every available location using considerPixelAt(), keeping track of the
# # minimum (best/closest) value returned and the location associated with it, this location "MinCoord"
# # is where we will place the target color
# @njit
def getBestPositionForColor(requestedColor):

    # reset minimums
    MinCoord = INVALID_COORD
    minDistance = sys.maxsize

    # for every available position in the boundry, perform the check, keep the best position:
    for available in isAvailable:

        # check = canvasTools.considerPixelAt(
        #     workingCanvas, available, requestedColor, MODE)
        # def minimumSelection(workingCanvas, available, requestedColor):

        neighborDifferences = numpy.zeros(8, numpy.uint32)

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        count_differences = 0
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                neighbor = numpy.array(
                    [(available[0] - 1 + i), (available[1] - 1 + j)], numpy.uint32)

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

                        neighborDifferences[count_differences] = euclidianDistanceAprox
                        count_differences += 1

        if (MODE == config.mode['MIN']):
            # check if the considered pixel has at least one valid neighbor
            if (count_differences):
                # return the minimum difference of all the neighbors
                check = numpy.min(neighborDifferences[0:count_differences])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize
        
        if (MODE == config.mode['AVG']):
            # check if the considered pixel has at least one valid neighbor
            if (count_differences):
                # return the minimum difference of all the neighbors
                check = numpy.mean(neighborDifferences[0:count_differences])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            MinCoord = numpy.array(available, numpy.uint32)

    return [requestedColor, MinCoord]


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requestedCoord):

    # Global Access
    global collisionCount
    global coloredCount
    global isAvailable
    global workingCanvas

    # Setup
    requestedCoordX = requestedCoord[0]
    requestedCoordY = requestedCoord[1]

    # double check the the pixel is BLACK
    isBlack = numpy.array_equal(workingCanvas[requestedCoord[0], requestedCoord[1]], BLACK)
    if (isBlack):

        # the best position for requestedColor has been found color it
        workingCanvas[requestedCoordX, requestedCoordY] = requestedColor

        # remove that position from isAvailable and increment the count
        isAvailable.remove(requestedCoord)
        coloredCount += 1

        # each valid neighbor position should be added to isAvailable
        for neighbor in canvasTools.removeColoredNeighbors(canvasTools.getNeighbors(workingCanvas, requestedCoord), workingCanvas):
            isAvailable.append(neighbor)

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
