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
CANVAS_HEIGHT = 128
CANVAS_WIDTH = 128
START_X = 64
START_Y = 64

# globals
isAvailable = []
allColors = []
start = []
myCanvas = canvas.Canvas(0,0)


def main():
    global isAvailable
    global allColors
    global start
    global myCanvas

    # Setup
    isAvailable = []
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH)
    start = [START_X, START_Y]
    myCanvas = canvas.Canvas(CANVAS_WIDTH, CANVAS_HEIGHT)

    # Work
    print("Painting Canvas...")
    beginTime = time.time()
    paintCanvas()
    elapsedTime = time.time() - beginTime

    # Final Print
    printCurrentCanvas()
    print("Painting Completed in " + "{:3.2f}".format(elapsedTime / 60) + " minutes!")
    


def printCurrentCanvas():
    global myCanvas

    # write the png file
    myFile = open('fuck1.png', 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, myCanvas.toRawOutput())
    myFile.close()


def paintCanvas():
    global allColors
    global myCanvas
    global start
    global isAvailable

    # draw the first color at the starting pixel
    targetColor = allColors.pop()
    myCanvas.setColorAt(targetColor, start)
    count = 1

    # add its neigbors to isAvailable
    for neighbor in myCanvas.getValidNeighbors(start):
        isAvailable.append(neighbor)

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
        count += 1
        isAvailable.remove(minCoord)

        # each adjacent position should be added to isAvailable, unless
        # it is already colored, it is already in the list, or it is outside the canvas
        for neighbor in myCanvas.getValidNeighbors(minCoord):
            if (myCanvas.getColorAt(neighbor) == BLACK):
                if not (neighbor in isAvailable):
                    isAvailable.append(neighbor)

        if (count % 100 == 0):
            printCurrentCanvas()


if __name__ == '__main__':
    main()
