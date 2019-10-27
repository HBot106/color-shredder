import colorTools
import numpy

class Canvas:
    # instantiates an all black canvas, a 2d list [height_pixels][width_pixels] of colors (all set to black)
    def __init__(self, width_pixels, height_pixels):
        self.width = width_pixels
        self.heigt = height_pixels
        self.canvas = []

        black = [0, 0, 0]

        # loop over the whole canvas, adding sub-lists of black color objects to a super-list
        for _ in range(self.width):
            column = []
            for _ in range(self.heigt):
                column.append(black)
            self.canvas.append(column)

    # takes the canvas (2d color list) and converts it to
    # the format [[r,g,b,r,g,b...],[r,g,b,r,g,b...]...]
    # for later writing to a png
    def toRawOutput(self):
        output = []
        for x in range(self.width):
            rowOutput = []
            for y in range(self.heigt):
                rowOutput += self.getColorAt([x, y])
            output.append(rowOutput)
        return output

    # set the color at a position in the canvas
    def setColorAt(self, color, coord):
        self.canvas[coord[0]][coord[1]] = color

    # get the color at a position in the canvas
    def getColorAt(self, coord):
        return self.canvas[coord[0]][coord[1]]

    def considerPixelAt(self, coord, targetColor, useAverage):
        neighborDifferences = []

        # loop over the 9 coordnates touching self (including self)
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    # this pixel is self, it is not a neigbor, go to the next one
                    continue

                # calculate the neigbor's coordinates
                neighbor = [coord[0] - 1 + i,
                            coord[1] - 1 + j]

                # if they are within the canvas add them to the final neigbor list
                if (0 <= neighbor[0] < self.width) and (0 <= neighbor[1] < self.heigt):
                    considerColor = self.canvas[neighbor[0]][neighbor[1]]
                    neighborDifferences.append(
                        colorTools.getColorDifferenceSquared(targetColor, considerColor))

        if (useAverage):
            output = numpy.average(neighborDifferences)
            neighborDifferences.clear()
            return output
        else:
            output = numpy.min(neighborDifferences)
            neighborDifferences.clear()
            return output

    # return a list of adjacent coordinates bounded by the canvas size
    def getValidNeighbors(self, target_coord):
        neighbors = []
        black = [0, 0, 0]

        # loop over the 9 coordnates touching self (including self)
        for i in range(3):
            for j in range(3):

                if (i == 1 and j == 1):
                    # this pixel is self, it is not a neigbor, go to the next one
                    continue

                # calculate the neigbor's coordinates
                neighbor = [target_coord[0] - 1 + i,
                            target_coord[1] - 1 + j]

                # if they are within the canvas add them to the final neigbor list
                if (0 <= neighbor[0] < self.width) and (0 <= neighbor[1] < self.heigt):
                    if (self.canvas[neighbor[0]][neighbor[1]] == black):
                        neighbors.append(neighbor)
        return neighbors
