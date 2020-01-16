import colorTools

import sys
import numpy

UNCOLORED = 1
COLORED = 2

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):

    # converts the given canvas into a format that the PNG module can use to write a png
    simpleCanvas = numpy.array(canvas, numpy.uint8)
    transposedCanvas = numpy.transpose(simpleCanvas, (1, 0, 2))
    flippedColors = numpy.flip(transposedCanvas, 2)
    rawOutput = numpy.reshape(
        flippedColors, (canvas.shape[1], canvas.shape[0] * 3))
    return rawOutput


# Gets either the mean or min value of all the colorDiffs of valid neighbors of the considered pixel
# # In other words it considers a location by calculating the euclidian color diiference between each of
# # the location's neigbors and the target color to be placed. It then gives back either the min of
# # these 8 values or the average of them.
def considerPixelAt(canvas, coordX, coordY, targetColor, useAverage):

    # Setup
    index = 0
    width = canvas.shape[0]
    height = canvas.shape[1]
    hasValidNeighbor = False
    neighborDifferences = numpy.zeros(8, numpy.uint32)

    # Get neighbors, Loop over the 3x3 grid surrounding the location being considered
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
                    hasValidNeighbor = True
                    index += 1

    # check if the considered pixel has at least one valid neighbor
    if (hasValidNeighbor):

        # either mean or min
        if (useAverage):
            return numpy.mean(neighborDifferences[0:index])
        else:
            return numpy.min(neighborDifferences[0:index])

    # if it has no valid neighbors, maximise its colorDiff
    else:
        return sys.maxsize


# Gives all valid locations surrounding a given location
def getNeighbors(canvas, coordX, coordY):

    # Setup
    index = 0
    neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            neighbor = numpy.array([(coordX - 1 + i), (coordY - 1 + j)], numpy.uint32)

            # neighbor must be in the canvas
            neighborIsInCanvas = ((0 <= neighbor[0] < canvas.shape[0])
                                  and (0 <= neighbor[1] < canvas.shape[1]))
            if (neighborIsInCanvas):
                neighbors[index] = neighbor
                index += 1
    if (index):
        return neighbors[]


# Of the 8 neighbors, filter out those not matching a given filter
index = 0
for neighbor in neighbors:

    # is the neighbor BLACK
    neighborIsBlack = numpy.array_equal(
            canvas[neighborX, neighborY], BLACK)

    # FILTER: neighbors must be BLACK
    if (condition == UNCOLORED):
        if (neighborIsBlack):
            # add to the list of valid neighbors
            requestedNeigbors[index] = numpy.array([neighbor, numpy.uint32)
            index += 1
            hasValidNeighbor = True

    # FILTER: neighbors must NOT be BLACK
    elif (condition=COLORED):

        if not (neighborIsBlack):
            # add to the list of valid neighbors
            requestedNeigbors[index] = numpy.array([neighbor, numpy.uint32)
            index += 1
            hasValidNeighbor = True

    # FILTER: None/Other
    else:
        # add all to the list of valid neighbors
            requestedNeigbors[index] = numpy.array([neighbor, numpy.uint32)
            index += 1
            hasValidNeighbor = True
