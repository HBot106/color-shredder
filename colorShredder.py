import png
import random
import sys

USE_AVERAGE = False
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 512
CANVAS_WIDTH = 512
START_X = 256
START_Y = 256


class Coords:
    # instantiates a coordinate
    def __init__(self, x_coord, y_coord):
        self.x = x_coord
        self.y = y_coord

    def __hash__(self):
        return self.x ^ self.y

    # checks for equaltiy with another coordinate
    def isEqual(self, check_coords):
        if ((self.x == check_coords.x) and (self.y == check_coords.y)):
            return True
        else:
            return False

    # return a list of adjacent coordinates bounded by the canvas size
    def getNeighbors(self):
        neighbors = []

        # loop over the 9 coordnates touching self (including self)
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    # this pixel is self, it is not a neigbor, go to the next one
                    continue

                # calculate the neigbor's coordinates
                neighborX = self.x - 1 + i
                neighborY = self.y - 1 + j

                # if they are within the canvas add them to the final neigbor list
                if (0 < neighborX < CANVAS_WIDTH) and (0 < neighborY < CANVAS_HEIGHT):
                    neighbors.append(Coords(neighborX, neighborY))
        return neighbors

    # debug print
    def printCoords(self):
        print("x: " + str(self.x) + ", y: " + str(self.y))


class Color:
    # instantiates a color
    def __init__(self, red, green, blue):
        self.r = red
        self.g = green
        self.b = blue

    # get the squared difference to another color
    def getColorDifferenceSquared(self, check_color):
        # I figure for minimization purposes distance^2 is just as good as distance
        r_comp = self.r - check_color.r
        g_comp = self.g - check_color.g
        b_comp = self.b - check_color.b
        return (r_comp * r_comp) + (g_comp * g_comp) + (b_comp * b_comp)

    # return the rgb values as a list
    def getRawColor(self):
        return [self.r, self.g, self.b]

    # checks for equaltiy with another color
    def isEqual(self, check_color):
        if ((self.r == check_color.r) and (self.g == check_color.g) and (self.b == check_color.b)):
            return True
        else:
            return False


class Canvas:
    # instantiates an all black canvas, a 2d list [height_pixels][width_pixels] of colors (all set to black)
    def __init__(self, width_pixels, height_pixels):
        self.width = width_pixels
        self.heigt = height_pixels
        self.canvas = []

        black = Color(0, 0, 0)

        # loop over the whole canvas, adding sub-lists of black color objects to a super-list
        for i in range(0, width_pixels):
            row = []
            for j in range(0, height_pixels):
                row.append(black)
            self.canvas.append(row)

    # takes the canvas (2d color list) and converts it to
    # the format [[r,g,b,r,g,b...],[r,g,b,r,g,b...]...]
    # for later writing to a png
    def toRawOutput(self):
        output = []
        for row in self.canvas:
            rowOutput = []
            for pixel in row:
                rowOutput += pixel.getRawColor()
            output.append(rowOutput)
        return output

    # set the color at a position in the canvas
    def setColorAt(self, color, coord):
        self.canvas[coord.y][coord.x] = color

    # get the color at a position in the canvas
    def getColorAt(self, coord):
        return self.canvas[coord.y][coord.x]

    def considerPixelAt(self, coord, targetColor):
        neighborDifferences = []

        # loop over the 9 coordnates touching self (including self)
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    # this pixel is self, it is not a neigbor, go to the next one
                    continue

                # calculate the neigbor's coordinates
                neighborX = coord.x - 1 + i
                neighborY = coord.y - 1 + j

                # if they are within the canvas add them to the final neigbor list
                if (0 < neighborX < CANVAS_WIDTH) and (0 < neighborY < CANVAS_HEIGHT):
                    neighborDifferences.append(
                        self.canvas[neighborX][neighborY].getColorDifferenceSquared(targetColor))

        if (USE_AVERAGE):
            return sum(neighborDifferences)//len(neighborDifferences)
        else:
            return min(neighborDifferences)

    # return a list of adjacent coordinates bounded by the canvas size
    def getValidNeighbors(self, target_coord):
        neighbors = []

        # loop over the 9 coordnates touching self (including self)
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    # this pixel is self, it is not a neigbor, go to the next one
                    continue

                # calculate the neigbor's coordinates
                neighbor = Coords(target_coord.x - 1 + i,
                                  target_coord.y - 1 + j)

                # if they are within the canvas add them to the final neigbor list
                if (0 < neighbor.x < self.width) and (0 < neighbor.y < self.heigt):
                    if (self.canvas[neighbor.y][neighbor.x].isEqual(Color(0, 0, 0))):
                        neighbors.append(neighbor)
        return neighbors


def generateColors():

    # setup
    allColors = []
    numberOfChannelValues = 2**COLOR_BIT_DEPTH
    totalNumber = numberOfChannelValues**3
    count = 0

    # loop over every color
    for r in range(numberOfChannelValues):
        for g in range(numberOfChannelValues):
            for b in range(numberOfChannelValues):
                # add each color
                allColors.append(Color(r, g, b))
                count += 1
        # print completion progress
        if ((count*100//totalNumber) % 10 == 0):
            print("Generating All Colors: " +
                  str(count*100//totalNumber) + "% ...")

    # shuffle the list of colors
    print("Shuffling...")
    random.shuffle(allColors)
    print("Shuffling Complete")

    return(allColors)


def main():
    # setup
    allColors = generateColors()
    myCanvas = Canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    start = Coords(START_X, START_Y)
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
    for available in isAvailable:
        available.printCoords()
    print("")

    for i in range(10000):
        targetColor = allColors.pop()
        minCoord = Coords(0, 0)
        minDistance = sys.maxsize

        for available in isAvailable:
            if not (myCanvas.getColorAt(available).isEqual(Color(0, 0, 0))):
                print("This pixel shouldn't be available.")
                print("Pixels Colored: " + str(count))
                print("Pixels Available: " + str(len(isAvailable)))
                for available in isAvailable:
                    available.printCoords()
                print("")
                exit(1)

            check = myCanvas.considerPixelAt(available, targetColor)
            if (check < minDistance):
                minDistance = check
                minCoord = available

        myCanvas.setColorAt(targetColor, minCoord)
        count += 1
        isAvailable.remove(minCoord)

        for neighbor in myCanvas.getValidNeighbors(minCoord):
            if (myCanvas.getColorAt(neighbor).isEqual(Color(0, 0, 0))):
                # 
                # DOESNT WORK
                # 
                if not (neighbor in isAvailable):
                    isAvailable.append(neighbor)

        if (i % 100 == 0):
            print("Pixels Colored: " + str(count))
            print("Pixels Available: " + str(len(isAvailable)))
            for available in isAvailable:
                available.printCoords()
            print("")
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


if __name__ == '__main__':
    main()
