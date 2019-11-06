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
USE_AVERAGE = True
SHUFFLE_COLORS = True
USE_MULTIPROCESSING = True
BLACK = numpy.zeros(3, numpy.int8)
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 100
CANVAS_WIDTH = 100
START_X = 0
START_Y = 0
PRINT_RATE = 100
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
ColoredCount = 0

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
        ColoredCount, len(isAvailable), (ColoredCount * 100 / CANVAS_WIDTH / CANVAS_HEIGHT), collisionCount, rate), end='\n')


def paintToCanvas(workerTargetColor, workerMinCoord):
    global collisionCount
    global ColoredCount
    global isAvailable
    global workingCanvas

    workerMinCoordX = workerMinCoord[0]
    workerMinCoordY = workerMinCoord[1]

    # double check the the pixel is available
    currentlyAvailable = isAvailable.get(
        workerMinCoord.tostring(), INVALID_COORD)
    availabilityCheck = not numpy.array_equal(
        currentlyAvailable, INVALID_COORD)
    if (availabilityCheck):

        # double check the the pixel is BLACK
        isBlack = numpy.array_equal(
            workingCanvas[currentlyAvailable[0], currentlyAvailable[1]], BLACK)
        if (isBlack):

            # the best position for workerTargetColor has been found color it
            workingCanvas[workerMinCoordX, workerMinCoordY] = workerTargetColor

            # remove that position from isAvailable and increment the count
            isAvailable.pop(workerMinCoord.tostring())
            ColoredCount += 1

            # each valid neighbor position should be added to isAvailable
            for neighbor in canvasTools.getValidNeighbors(workingCanvas, workerMinCoordX, workerMinCoordY):
                isAvailable.update({neighbor.data.tobytes(): neighbor})

        # collision
        else:
            collisionCount += 1

    # collision
    else:
        collisionCount += 1

    # print progress
    if (ColoredCount % PRINT_RATE == 0):
        printCurrentCanvas()


def paintCanvas():
    global colorIndex
    global isAvailable
    global allColors
    global workingCanvas
    global ColoredCount

    # draw the first color at the starting pixel
    targetColor = allColors[colorIndex]
    colorIndex += 1

    workingCanvas[START_X, START_Y] = targetColor

    # add its neigbors to isAvailable
    for neighbor in canvasTools.getValidNeighbors(workingCanvas, START_X, START_Y):
        isAvailable.update({neighbor.data.tobytes(): neighbor})

    # finish first pixel
    ColoredCount = 1
    printCurrentCanvas()

    printerManager = concurrent.futures.ThreadPoolExecutor()

    # while more uncolored boundry locations exist
    while(isAvailable.keys()):
        availableCount = len(isAvailable.keys())

        # continue painting
        if (availableCount > 2000):
            painterManager = concurrent.futures.ProcessPoolExecutor()
            painters = []

            for _ in range(min(((availableCount//250) + 1, 256))):
                # get the color to be placed
                targetColor = allColors[colorIndex]
                colorIndex += 1

                painters.append(painterManager.submit(
                    getBestPositionForColor, targetColor))

            for painter in concurrent.futures.as_completed(painters):
                workerResult = painter.result()
                workerTargetColor = workerResult[0]
                workerMinCoord = workerResult[1]

                paintToCanvas(workerTargetColor, workerMinCoord)

            painterManager.shutdown()

        else:
            # get the color to be placed
            targetColor = allColors[colorIndex]
            colorIndex += 1

            bestResult = getBestPositionForColor(targetColor)
            resultColor = bestResult[0]
            resultCoord = bestResult[1]

            paintToCanvas(resultColor, resultCoord)

    printerManager.shutdown()


def getBestPositionForColor(targetColor):
    global isAvailable
    global workingCanvas

    # reset minimums
    workerMinCoord = numpy.array([0, 0])
    minDistance = sys.maxsize

    # for every available position in the boundry, perform the check, keep the best position:
    for available in isAvailable.values():

        # consider the available location with the target color
        check = canvasTools.considerPixelAt(
            workingCanvas, available[0], available[1], targetColor, USE_AVERAGE)

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            workerMinCoord = numpy.array(available)

    return [targetColor, workerMinCoord]


if __name__ == '__main__':
    main()
