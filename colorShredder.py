import png
import random

USE_AVERAGE = False
COLOR_BIT_DEPTH = 8
CANVAS_HEIGHT = 4096
CANVAS_WIDTH = 4096
START_X = 128
START_Y = 128


class Coords:
    def __init__(self, x_coord, y_coord):
        self.x = x_coord
        self.y = y_coord

    def getHash(self):
        return self.x ^ self.y

    def isEqual(self, check_coords):
        if ((self.x == check_coords.x) and (self.y == check_coords.y)):
            return True
        else:
            return False

    def getNeighbors(self):
        neighbors = []
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    continue

                neighborX = self.x - 1 + i
                neighborY = self.y - 1 + j

                if (0 < neighborX < CANVAS_WIDTH) and (0 < neighborY < CANVAS_HEIGHT):
                    neighbors.append(Coords(neighborX, neighborY))

        return neighbors

    def printCoords(self):
        print("x: " + str(self.x))
        print("y: " + str(self.y))


class Color:
    def __init__(self, red, green, blue):
        self.r = red
        self.g = green
        self.b = blue

    def getColorDifferenceSquared(self, check_color):
        # I figure for minimization purposes distance^2 is just as good as distance
        r_comp = self.r - check_color.r
        g_comp = self.g - check_color.g
        b_comp = self.b - check_color.b
        return (r_comp * r_comp) + (g_comp * g_comp) + (b_comp * b_comp)

    def getRawColor(self):
        return [self.r, self.g, self.b]


def generateColors():
    allColors = []
    numberOfChannelValues = 2**COLOR_BIT_DEPTH

    for r in range(numberOfChannelValues):
        for g in range(numberOfChannelValues):
            for b in range(numberOfChannelValues):
                allColors.append(Color(r, g, b))

    random.shuffle(allColors)
    return(allColors)


def main():
    allColors = generateColors()

    p = [(255, 0, 0, 0, 255, 0, 0, 0, 255),
         (128, 0, 0, 0, 128, 0, 0, 0, 128)]
    f = open('2swatch.png', 'wb')
    w = png.Writer(3, 2, greyscale=False)
    w.write(f, p)
    f.close()


if __name__ == '__main__':
    main()
