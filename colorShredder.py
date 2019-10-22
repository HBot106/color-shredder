import png
import random

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
        print("x: " + str(self.x))
        print("y: " + str(self.y))


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
    isAvailable = set()

    # draw the first color at the starting pixel
    myCanvas.setColorAt(allColors.pop(), start)
    for neighbor in start.getNeighbors():
        isAvailable.add(neighbor)

    # write the png file
    myFile = open('fuck.png', 'wb')
    myWriter = png.Writer(CANVAS_WIDTH, CANVAS_HEIGHT, greyscale=False)
    myWriter.write(myFile, myCanvas.toRawOutput())
    myFile.close()


if __name__ == '__main__':
    main()
