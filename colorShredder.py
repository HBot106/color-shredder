import png
import random
import sys

import concurrent.futures
import time
import numpy

import colorTools
import canvasTools

# macros
FILENAME = "painting"
USE_AVERAGE = True
# BLACK = [0, 0, 0]
BLACK = numpy.zeros(3, numpy.int8)
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 100
CANVAS_WIDTH = 100
START_X = 0
START_Y = 0

# globals
colorIndex = 0
printCount = 0
printTime = time.time()
collisionCount = 0
totalColored = 0
totalColors = 0
isAvailable = []
allColors = []
startCoords = []
workingCanvas = []


def main():
    global totalColors
    global isAvailable
    global allColors
    global startCoords
    global workingCanvas

    # Setup
    isAvailable = []
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH)
    totalColors = len(allColors)
    startCoords = [START_X, START_Y]
    # Builds a 3D list of the following form:
    # [ [BLACK, BLACK, BLACK, ...]
    #   [BLACK, BLACK, BLACK, ...]
    #   [BLACK, BLACK, BLACK, ...]...]
    # where  BLACK = [0, 0, 0]
    workingCanvas = canvasTools.constructBlank(CANVAS_WIDTH, CANVAS_HEIGHT)
    # therefore workingCanvas[x][y] is a list coresponding to the color of a pixel: [r, g, b]

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
    global printCount
    global printTime
    global workingCanvas

    beginTime = time.time()
    rate = 100/(beginTime - printTime)


    # write the png file
    name = (FILENAME + '.png')
    myFile = open(name, 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
    myFile.close()
    printCount += 1

    printTime = time.time()
    elapsedTime = printTime - beginTime
    

    print("Pixels Colored: " + str(totalColored) + ", Pixels Available: " + str(len(isAvailable)) +
          ", Percent Complete: " + "{:3.2f}".format(totalColored * 100 / CANVAS_WIDTH / CANVAS_HEIGHT) + 
          "%, PNG written in " + "{:3.2f}".format(elapsedTime) + " seconds, Total Collisions: " + 
          str(collisionCount) + ", Rate: "  + "{:3.2f}".format(rate) + " pixels/sec." , end='\n')


def paintToCanvas(workerOutput):
    global collisionCount
    global totalColored
    global isAvailable
    global workingCanvas

    workerTargetColor = workerOutput[0]
    workerMinCoord = workerOutput[1]
    # double check the the pixel is both available and hasnt been colored yet
    if (workerMinCoord in isAvailable) and (canvasTools.getColorAt(workingCanvas, workerMinCoord).all() == BLACK.all()):

        # the best position for workerTargetColor has been found; color it,
        # increment the count, and remove that position from isAvailable
        canvasTools.setColorAt(
            workingCanvas, workerTargetColor, workerMinCoord)
        isAvailable.remove(workerMinCoord)
        totalColored += 1

        # each adjacent position should be added to isAvailable, unless
        # it is already colored, it is already in the list, or it is outside the canvas
        for neighbor in canvasTools.getValidNeighbors(workingCanvas, workerMinCoord):
            if not (neighbor in isAvailable):
                isAvailable.append(neighbor)

    # we could just discard the pixel in the case of a collision, but for
    # the sake of completeness we will add it back to the allColors list since it was popped
    else:
        allColors.append(workerTargetColor)
        collisionCount += 1
        # print("[Collision]")

    if (totalColored % 100 == 0):
        printCurrentCanvas()


def paintCanvas():
    global colorIndex
    global isAvailable
    global allColors
    global workingCanvas
    global totalColored

    # draw the first color at the starting pixel
    targetColor = allColors[colorIndex]
    colorIndex += 1

    canvasTools.setColorAt(workingCanvas, targetColor, startCoords)

    # add its neigbors to isAvailable
    for neighbor in canvasTools.getValidNeighbors(workingCanvas, startCoords):
        isAvailable.append(neighbor)

    # finish first pixel
    totalColored = 1
    printCurrentCanvas()

    printerManager = concurrent.futures.ThreadPoolExecutor()

    # while more uncolored boundry locations exist
    while(isAvailable):
        availableCount = len(isAvailable)

        # continue painting
        if (availableCount > 2000):
            painterManager = concurrent.futures.ProcessPoolExecutor()
            painters = []

            for _ in range(min(((availableCount//250) + 1, 64))):
                # get the color to be placed
                targetColor = allColors[colorIndex]
                colorIndex += 1

                painters.append(painterManager.submit(
                    getBestPositionForColor, targetColor))

            for painter in concurrent.futures.as_completed(painters):
                paintToCanvas(painter.result())

            painterManager.shutdown()

        else:
            # get the color to be placed
            targetColor = allColors[colorIndex]
            colorIndex += 1

            paintToCanvas(getBestPositionForColor(targetColor))

    printerManager.shutdown()


def getBestPositionForColor(targetColor):
    global isAvailable
    global workingCanvas

    # reset minimums
    workerMinCoord = [0, 0]
    minDistance = sys.maxsize

    # for every available position in the boundry, perform the check, keep the best position:
    for available in isAvailable:

        # consider the available location with the target color
        check = canvasTools.considerPixelAt(
            workingCanvas, available, targetColor, USE_AVERAGE)

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            workerMinCoord = available

    return [targetColor, workerMinCoord]


if __name__ == '__main__':
    main()
