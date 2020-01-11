import png
import numpy

import os
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

LOCATIONS_PER_PAINTER = 50
MAX_PAINTERS = os.cpu_count() * 2
MIN_MULTI_WORKLOAD = 200

BLACK = numpy.array([0, 0, 0])

COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 64
CANVAS_WIDTH = 64
START_X = 32
START_Y = 32

PRINT_RATE = 10
INVALID_COORD = numpy.array([-1, -1])

# =============================================================================
# GLOBALS
# =============================================================================

# position in and the list of all colors to be placed
colorIndex = 0
allColors = numpy.zeros([((2**COLOR_BIT_DEPTH)**3), 3])

# used for ongoing speed calculation
lastPrintTime = time.time()

# tracked for informational printout / progress report
collisionCount = 0
coloredCount = 0

# dictionary used for lookup of available locations
isAvailable = {}

# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_WIDTH, CANVAS_HEIGHT, 3], numpy.uint8)

# writes data arrays as PNG image files
pngWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)

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
    while(isAvailable.keys() and (colorIndex < allColors.shape[0])):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
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

    # Global Access
    global colorIndex
    global isAvailable
    global workingCanvas
    global coloredCount

    # Setup
    availableCount = len(isAvailable.keys())

    # if more than MIN_MULTI_WORKLOAD locations are available, allow multiprocessing
    if ((availableCount > MIN_MULTI_WORKLOAD) and USE_MULTIPROCESSING):
        painterManager = concurrent.futures.ProcessPoolExecutor()
        painters = []

        # cap the number of workers so that there are at least 250 free locations per worker
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

    # Global Access
    global collisionCount
    global coloredCount
    global isAvailable
    global workingCanvas

    # Setup
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
        if (rate > 1000) and not (finalize):
            return

        # write the png file
        name = (FILENAME + '.png')
        myFile = open(name, 'wb')
        pngWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
        myFile.close()

        # Info Print
        lastPrintTime = currentTime
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            coloredCount, len(isAvailable), (coloredCount * 100 / CANVAS_WIDTH / CANVAS_HEIGHT), collisionCount, rate), end='\n')


if __name__ == '__main__':
    main()
