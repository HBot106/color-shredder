import png
import numpy

import random
import sys
import concurrent.futures
import time

import colorTools
import canvasTools

# =============================================================================
# MACROS
# =============================================================================

FILENAME = "painting"

USE_AVERAGE = False
SHUFFLE_COLORS = True
USE_MULTIPROCESSING = True

MAX_PAINTERS = 256

BLACK = numpy.array([0, 0, 0])
WHITE = numpy.array([255, 255, 255])
RED = numpy.array([255, 0, 0])
GREEN = numpy.array([0, 255, 0])
BLUE = numpy.array([0, 0, 255])

COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 64
CANVAS_WIDTH = 64
START_X = 32
START_Y = 32

PRINT_RATE = 1
INVALID_COORD = numpy.array([-1, -1])

# =============================================================================
# GLOBALS
# =============================================================================

# position in and the list of all colors to be placed
colorIndex = 0
allColors = numpy.zeros([((2**COLOR_BIT_DEPTH)**3), 3], numpy.uint8)

# used for ongoing speed calculation
printTime = time.time()

# tracked for informational printout / progress report
collisionCount = 0
coloredCount = 0

# dictionary used for lookup of available locations
isAvailable = {}

# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_WIDTH, CANVAS_HEIGHT, 3], numpy.uint8)

# =============================================================================


def main():
    global allColors

    # Setup
    allColors = colorTools.generateColors(
        COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    beginTime = time.time()
    paintCanvas()
    elapsedTime = time.time() - beginTime

    # Final Print
    printCurrentCanvas()
    print("Painting Completed in " +
          "{:3.2f}".format(elapsedTime / 60) + " minutes!")


# manages painting of the canvas
def paintCanvas():

    # draw the first color at the starting pixel
    startPainting()

    # while more un-colored boundry locations exist and there are more colors to be placed, continue painting
    while(isAvailable.keys() and (colorIndex < allColors.shape[0])):
        continuePainting()


# start the painting
def startPainting():
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    # draw the first color at the starting pixel
    targetColor = allColors[colorIndex]
    workingCanvas[START_X, START_Y] = targetColor
    colorIndex += 1

    # add its neigbors to isAvailable
    for neighbor in canvasTools.getValidNeighbors(workingCanvas, START_X, START_Y):
        isAvailable.update({neighbor.data.tobytes(): neighbor})

    # finish first pixel
    coloredCount = 1
    printCurrentCanvas()


# continue the painting
def continuePainting():
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    availableCount = len(isAvailable.keys())

    # if more than 2000 locations are available, allow multiprocessing
    if ((availableCount > 2000) and USE_MULTIPROCESSING):
        painterManager = concurrent.futures.ProcessPoolExecutor()
        painters = []

        # cap the number of workers so that there are at least 250 free lcoations per worker
        for _ in range(min(((availableCount//250) + 1, MAX_PAINTERS))):

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

        painterManager.shutdown()

    # otherwise, use only this process
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


# gives the best location among all avilable for the requested color
# also returns the color itself
def getBestPositionForColor(requestedColor):

    # reset minimums
    MinCoord = INVALID_COORD
    minDistance = sys.maxsize

    # for every available position in the boundry, perform the check, keep the best position:
    for available in isAvailable.values():

        # consider the available location with the target color
        check = canvasTools.considerPixelAt(
            workingCanvas, available[0], available[1], requestedColor, USE_AVERAGE)

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            MinCoord = numpy.array(available)

    return [requestedColor, MinCoord]


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requestedCoord):
    global collisionCount
    global coloredCount
    global isAvailable
    global workingCanvas

    requestedCoordX = requestedCoord[0]
    requestedCoordY = requestedCoord[1]

    # double check the the pixel is available
    currentlyAvailable = isAvailable.get(
        requestedCoord.tostring(), INVALID_COORD)
    availabilityCheck = not numpy.array_equal(
        currentlyAvailable, INVALID_COORD)
    if (availabilityCheck):

        # double check the the pixel is BLACK
        isBlack = numpy.array_equal(
            workingCanvas[currentlyAvailable[0], currentlyAvailable[1]], BLACK)
        if (isBlack):

            # the best position for requestedColor has been found color it
            workingCanvas[requestedCoordX, requestedCoordY] = requestedColor

            # remove that position from isAvailable and increment the count
            isAvailable.pop(requestedCoord.tostring())
            coloredCount += 1

            # each valid neighbor position should be added to isAvailable
            for neighbor in canvasTools.getValidNeighbors(workingCanvas, requestedCoordX, requestedCoordY):
                isAvailable.update({neighbor.data.tobytes(): neighbor})

        # collision
        else:
            collisionCount += 1

    # collision
    else:
        collisionCount += 1

    # print progress
    if (coloredCount % PRINT_RATE == 0):
        printCurrentCanvas()


# prints the current state of workingCanvas as well as progress stats
def printCurrentCanvas():
    global printTime

    beginTime = time.time()
    rate = 100/(beginTime - printTime)

    # write the png file
    name = (FILENAME + '.png')
    myFile = open(name, 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
    myFile.close()

    printTime = time.time()

    print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
        coloredCount, len(isAvailable), (coloredCount * 100 / CANVAS_WIDTH / CANVAS_HEIGHT), collisionCount, rate), end='\n')

    # time.sleep(.5)


if __name__ == '__main__':
    main()
