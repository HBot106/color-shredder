import png
import random
import sys

import colorTools
import canvas

USE_AVERAGE = False
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 128
CANVAS_WIDTH = 128
START_X = 0
START_Y = 0


def main():
    # setup
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH)
    myCanvas = canvas.Canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    start = [START_X, START_Y]
    isAvailable = []
    count = 0

    # draw the first color at the starting pixel
    targetColor = allColors.pop()
    myCanvas.setColorAt(targetColor, start)
    count += 1
    for neighbor in myCanvas.getValidNeighbors(start):
        isAvailable.append(neighbor)

    print("Pixels Colored: " + str(count))
    print("Pixels Available: " + str(len(isAvailable)))
    print("")

    while(isAvailable):
        minCoord = [0, 0]
        black = [0, 0, 0]
        targetColor = allColors.pop()
        minDistance = sys.maxsize

        for available in isAvailable:

            check = myCanvas.considerPixelAt(
                available, targetColor, USE_AVERAGE)
            if (check < minDistance):
                minDistance = check
                minCoord = available

        myCanvas.setColorAt(targetColor, minCoord)
        count += 1
        isAvailable.remove(minCoord)

        for neighbor in myCanvas.getValidNeighbors(minCoord):
            if (myCanvas.getColorAt(neighbor) == black):
                if not (neighbor in isAvailable):
                    isAvailable.append(neighbor)

        if (count % 100 == 0):
            print("Pixels Colored: " + str(count))
            print("Pixels Available: " + str(len(isAvailable)))

            # write the png file
            myFile = open('fuck1.png', 'wb')
            myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
            myWriter.write(myFile, myCanvas.toRawOutput())
            myFile.close()

    # write the png file
    myFile = open('fuck1.png', 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, myCanvas.toRawOutput())
    myFile.close()

    print("Pixels Colored: " + str(count))
    print("Pixels Available: " + str(len(isAvailable)))
    print("Finished")


if __name__ == '__main__':
    main()
