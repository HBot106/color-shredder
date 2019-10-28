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
CANVAS_HEIGHT = 64
CANVAS_WIDTH = 64
START_X = 32
START_Y = 32

# globals
printCount = 0
totalColored = 0
totalColors = 0
isAvailable = []
allColors = []
startCoords= []
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

    # write the png file
    name = (FILENAME + '.png')
    myFile = open(name, 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
    myFile.close()
    printCount += 1

    print("Pixels Colored: " + str(totalColored) + ", Pixels Available: " + str(len(isAvailable)) +
          ", Percent Complete: " + "{:3.2f}".format(totalColored * 100 / CANVAS_WIDTH / CANVAS_HEIGHT) + "%", end='\n')


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

    # while more uncolored boundry locations exist
    while(isAvailable):

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

        # the best position for targetColor has been found; color it,
        # increment the count, and remove that position from isAvailable
        canvasTools.setColorAt(workingCanvas, targetColor, minCoord)
        totalColored += 1
        isAvailable.remove(minCoord)

        # each adjacent position should be added to isAvailable, unless
        # it is already colored, it is already in the list, or it is outside the canvas
        for neighbor in canvasTools.getValidNeighbors(workingCanvas, minCoord):
            if not (neighbor in isAvailable):
                isAvailable.append(neighbor)

        if (totalColored % 25 == 0):
            printCurrentCanvas()


if __name__ == '__main__':
    main()
