import png
import numpy

from numba import njit

import os
import sys
import concurrent.futures
import time

import colorTools
import config

# =============================================================================
# MACROS
# =============================================================================
FILENAME = "painting"

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
INVALID_COORD = numpy.array([-1, -1])

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
count_available = 0
list_availabilty = []
canvas_availabilty = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.bool)
# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# writes data arrays as PNG image files
pngWriter = png.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

# =============================================================================


def main():
    # Global Access
    global allColors

    # Setup
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    beginTime = time.time()
    paintCanvas()
    elapsedTime = time.time() - beginTime

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(elapsedTime / 60) + " minutes!")


# manages painting of the canvas
def paintCanvas():

    # draw the first color at the starting pixel
    startPainting()

    # while more un-colored boundry locations exist and there are more colors to be placed, continue painting
    while(count_available and (colorIndex < allColors.shape[0])):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global colorIndex
    global count_available
    global list_availabilty
    global canvas_availabilty
    global workingCanvas
    global coloredCount

    # Setup
    targetColor = allColors[colorIndex]

    # draw the first color at the starting pixel
    workingCanvas[START_POINT[0], START_POINT[1]] = targetColor
    colorIndex += 1

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((START_POINT[0] - 1 + i), (START_POINT[1] - 1 + j))

            # neighbor must be in the canvas
            neighborIsInCanvas = ((0 <= coordinate_neighbor[0] < workingCanvas.shape[0]) and (0 <= coordinate_neighbor[1] < workingCanvas.shape[1]))

            if (neighborIsInCanvas):
                if (numpy.array_equal(workingCanvas[coordinate_neighbor[0], coordinate_neighbor[1]], BLACK)):
                    markCoordinate_Available(coordinate_neighbor)

    # finish first pixel
    coloredCount = 1
    printCurrentCanvas(True)


# continue the painting
def continuePainting():

    # Global Access
    global colorIndex
    global count_available
    global list_availabilty
    global canvas_availabilty
    global workingCanvas
    global coloredCount

    # Setup
    # if more than MIN_MULTI_WORKLOAD locations are coordinate_available, allow multiprocessing
    if ((count_available > MIN_MULTI_WORKLOAD) and USE_MULTIPROCESSING):
        painterManager = concurrent.futures.ProcessPoolExecutor()
        painters = []

        # cap the number of workers so that there are at least LOCATIONS_PER_PAINTER free locations per worker
        # this keeps the number of collisions down
        # loop over each one
        for _ in range(min(((count_available//LOCATIONS_PER_PAINTER), MAX_PAINTERS))):

            if(len(allColors) > colorIndex):
                # get the color to be placed
                targetColor = allColors[colorIndex]
                colorIndex += 1

                # schedule a worker to find the best location for that color
                neighborDifferences = numpy.zeros(8, numpy.uint32)
                painters.append(painterManager.submit(getBestPositionForColor, targetColor, neighborDifferences, numpy.array(list_availabilty), workingCanvas))

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
        bestResult = getBestPositionForColor(targetColor, neighborDifferences, numpy.array(list_availabilty), workingCanvas)
        resultColor = bestResult[0]
        resultCoord = bestResult[1]

        # attempt to paint the color at the corresponding location
        paintToCanvas(resultColor, resultCoord)


# Gives the best location among all avilable for the requested color; Also returns the color itself
# # In other words, checks every coordinate_available location using considerPixelAt(), keeping track of the
# # minimum (best/closest) value returned and the location associated with it, this location "MinCoord"
# # is where we will place the target color
# @njit
def getBestPositionForColor(rgb_requested_color, list_neighbor_diffs, list_available_coordinates, canvas_painting):

    # reset minimums
    MinCoord = INVALID_COORD
    minDistance = sys.maxsize

    # for every coordinate_available position in the boundry, perform the check, keep the best position:
    for coordinate_available in list_available_coordinates:

        index = 0
        list_neighbor_diffs.fill(0)

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                coordinate_neighbor = ((coordinate_available[0] - 1 + i), (coordinate_available[1] - 1 + j))

                # neighbor must be in the canvas
                neighborIsInCanvas = ((0 <= coordinate_neighbor[0] < canvas_painting.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_painting.shape[1]))

                if (neighborIsInCanvas):

                    neighborNotBlack = not numpy.array_equal(canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]], BLACK)
                    if (neighborNotBlack):

                        # get colDiff between the neighbor and target colors, add it to the list
                        neigborColor = canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]]

                        # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                        colorDifference = numpy.subtract(rgb_requested_color, neigborColor)
                        differenceSquared = numpy.multiply(colorDifference, colorDifference)
                        squaresSum = numpy.sum(differenceSquared)
                        euclidianDistanceAprox = squaresSum

                        list_neighbor_diffs[index] = euclidianDistanceAprox
                        index += 1

        if (config.mode['CURRENT'] == 0):
            # check if the considered pixel has at least one valid neighbor
            if (index):
                # return the minimum difference of all the neighbors
                check = numpy.min(list_neighbor_diffs[0:index])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize

        if (config.mode['CURRENT'] == 1):
            # check if the considered pixel has at least one valid neighbor
            if (index):
                # return the minimum difference of all the neighbors
                check = numpy.mean(list_neighbor_diffs[0:index])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                check = sys.maxsize

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            MinCoord = coordinate_available

    return (rgb_requested_color, MinCoord)


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requestedCoord):

    # Global Access
    global collisionCount
    global coloredCount
    global count_available
    global list_availabilty
    global canvas_availabilty
    global workingCanvas

    # double check the the pixel is BLACK
    isBlack = numpy.array_equal(workingCanvas[requestedCoord[0], requestedCoord[1]], BLACK)
    if (isBlack):

        # the best position for requestedColor has been found color it, and mark it unavailable
        workingCanvas[requestedCoord[0], requestedCoord[1]] = requestedColor
        markCoordinate_Unavailable(requestedCoord)
        coloredCount += 1

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                coordinate_neighbor = ((requestedCoord[0] - 1 + i), (requestedCoord[1] - 1 + j))

                # neighbor must be in the canvas
                neighborIsInCanvas = ((0 <= coordinate_neighbor[0] < workingCanvas.shape[0]) and (0 <= coordinate_neighbor[1] < workingCanvas.shape[1]))

                if (neighborIsInCanvas):
                    if (numpy.array_equal(workingCanvas[coordinate_neighbor[0], coordinate_neighbor[1]], BLACK)):
                        markCoordinate_Available(coordinate_neighbor)

    # collision
    else:
        collisionCount += 1

    # print progress
    if (coloredCount % PRINT_RATE == 0):
        printCurrentCanvas()


def markCoordinate_Available(requested_coordinate):

    global count_available
    global list_availabilty
    global canvas_availabilty

    if (not canvas_availabilty[requested_coordinate[0], requested_coordinate[1]]):
        list_availabilty.append(requested_coordinate)
        canvas_availabilty[requested_coordinate[0], requested_coordinate[1]] = True
        count_available += 1


def markCoordinate_Unavailable(requested_coordinate):

    global count_available
    global list_availabilty
    global canvas_availabilty

    list_availabilty.remove((requested_coordinate[0], requested_coordinate[1]))
    canvas_availabilty[requested_coordinate[0], requested_coordinate[1]] = False
    count_available -= 1


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):

    # converts the given canvas into a format that the PNG module can use to write a png
    simpleCanvas = numpy.array(canvas, numpy.uint8)
    transposedCanvas = numpy.transpose(simpleCanvas, (1, 0, 2))
    flippedColors = numpy.flip(transposedCanvas, 2)
    rawOutput = numpy.reshape(flippedColors, (canvas.shape[1], canvas.shape[0] * 3))
    return rawOutput


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
        pngWriter.write(myFile, toRawOutput(workingCanvas))
        myFile.close()

        # Info Print
        lastPrintTime = currentTime
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(coloredCount, count_available, (coloredCount * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), collisionCount, rate), end='\n')

    if (config.painter['DEBUG_WAIT']):
        time.sleep(3)


if __name__ == '__main__':
    main()
