import colorTools

import sys
import numpy

# BLACK reference
BLACK = numpy.zeros(3, numpy.uint8)


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):
    # takes the canvas in the form:
    # [   [[r,g,b], [r,g,b], [r,g,b]...],
    #     [[r,g,b], [r,g,b], [r,g,b]...]...]
    # and converts it to the format:
    # [   [r,g,b,r,g,b...],
    #     [r,g,b,r,g,b...]...]
    return canvas.transpose(1, 0, 2).reshape(-1, canvas[0].size)


def considerPixelAt(canvas, coordX, coordY, targetColor, useAverage):
    index = 0
    width = canvas.size
    height = canvas[0].size
    output = sys.maxsize
    neighborDifferences = numpy.zeros(8, numpy.uint64)

    # loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            neighborX = coordX - 1 + i
            neighborY = coordY - 1 + j

            # conditions for considering a neighbor
            neighborIsInCanvas = ((0 <= neighborX < width)
                                  and (0 <= neighborY < height))
            neighborIsBlack = numpy.array_equal(
                canvas[neighborX, neighborY], BLACK)
            if (neighborIsInCanvas and not neighborIsBlack):

                # get colDiff between the neighbor and target colors, add it to the list
                neigborColor = canvas[neighborX, neighborY]
                neighborDifferences[index] = colorTools.getColorDiffSquared(
                    targetColor, neigborColor)
                index += 1

    hasValidNeighbor = not numpy.array_equal(
        neighborDifferences, numpy.zeros(8, numpy.uint8))

    if (useAverage and hasValidNeighbor):
        output = numpy.mean(neighborDifferences[0:index])
        return output
    elif(hasValidNeighbor):
        output = numpy.amin(neighborDifferences[0:index])
        return output
    else:
        return output


def getValidNeighbors(canvas, coordX, coordY):
    index = 0
    width = canvas.size
    height = canvas[0].size
    neighbors = numpy.zeros([8, 2], numpy.uint8)

    # loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            neighborX = coordX - 1 + i
            neighborY = coordY - 1 + j

            # if they are within the canvas add them to the final neigbor list
            if (0 <= neighborX < width) and (0 <= neighborY < height) and (canvas[neighborX, neighborY].all() == BLACK.all()):
                neighbors[index] = numpy.array([neighborX, neighborY])
                index += 1

    return neighbors[0:index]
