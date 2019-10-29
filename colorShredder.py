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
BLACK = [0, 0, 0]
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 32
CANVAS_WIDTH = 256
START_X = 0
START_Y = 16

# globals
printCount = 0
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
    global workingCanvas

    beginTime = time.time()

    # write the png file
    name = (FILENAME + '.png')
    myFile = open(name, 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
    myFile.close()
    printCount += 1

    elapsedTime = time.time() - beginTime

    print("Pixels Colored: " + str(totalColored) + ", Pixels Available: " + str(len(isAvailable)) +
          ", Percent Complete: " + "{:3.2f}".format(totalColored * 100 / CANVAS_WIDTH / CANVAS_HEIGHT) + "%, PNG written in " + "{:3.2f}".format(elapsedTime) + " seconds.", end='\n')


def continuouslyPrintCurrentCanvas(interval):
    while(isAvailable):
        printCurrentCanvas()
        time.sleep(interval)


def paintCanvas():
    global totalColored
    global isAvailable
    global allColors
    global workingCanvas

    # draw the first color at the starting pixel
    targetColor = allColors.pop()
    canvasTools.setColorAt(workingCanvas, targetColor, startCoords)

    # add its neigbors to isAvailable
    for neighbor in canvasTools.getValidNeighbors(workingCanvas, startCoords):
        isAvailable.append(neighbor)

    # finish first pixel
    totalColored = 1
    printCurrentCanvas()

    # ThreadPoolExecutors for painting the canvas and printing the PNG
    painter = concurrent.futures.ThreadPoolExecutor()
    printer = concurrent.futures.ThreadPoolExecutor()

    # while more uncolored boundry locations exist
    # printer.submit(continuouslyPrintCurrentCanvas, 0.5)
    while(isAvailable):
        # continue painting
        paintCanvasWorker()
        if (totalColored % 100 == 0):
            printCurrentCanvas()

    printer.shutdown()


def paintCanvasWorker():
    global totalColored
    global isAvailable
    global allColors
    global workingCanvas

    # reset minimums
    minCoord = [0, 0]
    minDistance = sys.maxsize

    # get the color to be placed
    targetColor = allColors.pop()

    # for every available position in the boundry, perform the check, keep the best position:
    for available in isAvailable:

        # consider the available location with the target color
        check = canvasTools.considerPixelAt(
            workingCanvas, available, targetColor, USE_AVERAGE)

        # if it is the best so far save the value and its location
        if (check < minDistance):
            minDistance = check
            minCoord = available

    # double check the the pixel is both available and hasnt been colored yet
    if (minCoord in isAvailable) and (canvasTools.getColorAt(workingCanvas, minCoord) == BLACK):

        # the best position for targetColor has been found; color it,
        # increment the count, and remove that position from isAvailable
        canvasTools.setColorAt(workingCanvas, targetColor, minCoord)
        isAvailable.remove(minCoord)
        totalColored += 1

        # each adjacent position should be added to isAvailable, unless
        # it is already colored, it is already in the list, or it is outside the canvas
        for neighbor in canvasTools.getValidNeighbors(workingCanvas, minCoord):
            if not (neighbor in isAvailable):
                isAvailable.append(neighbor)

    # we could just discard the pixel in the case of a collision, but for
    # the sake of completeness we will add it back to the allColors list since it was popped
    else:
        allColors.append(targetColor)
        print("[Collision]")


if __name__ == '__main__':
    main()
