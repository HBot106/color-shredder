import colorTools

import sys
import numpy

# BLACK reference
BLACK = numpy.zeros(3, numpy.uint8)


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):
    return canvas.transpose(1, 0, 2).reshape(-1, canvas[0].size)


# gets either the mean or min value of all the colorDiffs of valid neighbors of the considered pixel
def considerPixelAt(canvas, coordX, coordY, targetColor, useAverage):
    index = 0
    width = canvas.shape[0]
    height = canvas.shape[1]
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

            # neighbor must be in the canvas
            neighborIsInCanvas = ((0 <= neighborX < width)
                                  and (0 <= neighborY < height))
            if (neighborIsInCanvas):

                # neighbor must not be BLACK
                neighborIsBlack = numpy.array_equal(
                    canvas[neighborX, neighborY], BLACK)
                if not (neighborIsBlack):

                    # get colDiff between the neighbor and target colors, add it to the list
                    neigborColor = canvas[neighborX, neighborY]
                    neighborDifferences[index] = colorTools.getColorDiff(
                        targetColor, neigborColor)
                    index += 1

    # check if the considered pixel has at least one valid neighbor
    hasValidNeighbor = not numpy.array_equal(
        neighborDifferences, numpy.zeros(8, numpy.uint8))
    if (hasValidNeighbor):

        # either mean or min
        if (useAverage):
            return numpy.mean(neighborDifferences[0:index])
        else:
            return numpy.amin(neighborDifferences[0:index])

    # if it has no valid neighbors, maximise its colorDiff
    else:
        return sys.maxsize


def getValidNeighbors(canvas, coordX, coordY):
    index = 0
    width = canvas.shape[0]
    height = canvas.shape[1]
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

            # neighbor must be in the canvas
            neighborIsInCanvas = ((0 <= neighborX < width)
                                  and (0 <= neighborY < height))
            if (neighborIsInCanvas):

                # neighbor must be BLACK
                neighborIsBlack = numpy.array_equal(
                    canvas[neighborX, neighborY], BLACK)
                if (neighborIsBlack):

                    # add to the list of valid neighbors
                    neighbors[index] = numpy.array([neighborX, neighborY])
                    index += 1

    # check if the considered pixel has at least one valid neighbor
    hasValidNeighbor = not numpy.array_equal(
        neighbors, numpy.zeros([8, 2], numpy.uint8))
    if (hasValidNeighbor):
        return neighbors[0:index]

    # if it has no valid neighbors, give none
    else:
        return numpy.array([])
