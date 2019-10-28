import png
import random
import sys

import concurrent.futures
import time
import numpy

import colorTools
import canvas

# macros
USE_AVERAGE = False
BLACK = [0, 0, 0]
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 64
CANVAS_WIDTH = 64
START_X = 32
START_Y = 32

# globals
totalColored = 0
totalColors = 0
isAvailable = []
allColors = []
start = []
myCanvas = canvas.Canvas(0, 0)


def main():
    global totalColored
    global totalColors
    global isAvailable
    global allColors
    global start
    global myCanvas

    # Setup
    isAvailable = []
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH)
    totalColors = len(allColors)
    start = [START_X, START_Y]
    myCanvas = canvas.Canvas(CANVAS_WIDTH, CANVAS_HEIGHT)

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
    global totalColored
    global totalColors
    global isAvailable
    global allColors
    global start
    global myCanvas

    # write the png file
    myFile = open('fuck0.png', 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, myCanvas.toRawOutput())
    myFile.close()

    print("Pixels Colored: " + str(totalColored) + ", Pixels Available: " + str(len(isAvailable)) +
          ", Percent Complete: " + "{:3.2f}".format(totalColored * 100 / CANVAS_WIDTH / CANVAS_HEIGHT) + "%", end='\n')


def paintCanvas():
    global totalColored
    global totalColors
    global isAvailable
    global allColors
    global start
    global myCanvas

    # draw the first color at the starting pixel
    targetColor = allColors.pop()
    myCanvas.setColorAt(targetColor, start)

    # add its neigbors to isAvailable
    for neighbor in myCanvas.getValidNeighbors(start):
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
            check = myCanvas.considerPixelAt(
                available, targetColor, USE_AVERAGE)

            # if it is the best so far save the value and its location
            if (check < minDistance):
                minDistance = check
                minCoord = available

        # the best position for targetColor has been found; color it,
        # increment the count, and remove that position from isAvailable
        myCanvas.setColorAt(targetColor, minCoord)
        totalColored += 1
        isAvailable.remove(minCoord)

        # each adjacent position should be added to isAvailable, unless
        # it is already colored, it is already in the list, or it is outside the canvas
        for neighbor in myCanvas.getValidNeighbors(minCoord):
            if (myCanvas.getColorAt(neighbor) == BLACK):
                if not (neighbor in isAvailable):
                    isAvailable.append(neighbor)

        if (totalColored % 25 == 0):
            printCurrentCanvas()


if __name__ == '__main__':
    main()
