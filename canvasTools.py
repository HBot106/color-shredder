import colorTools

import sys
import numpy

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):

    # converts the given canvas into a format that the PNG module can use to write a png
    simpleCanvas = numpy.array(canvas, numpy.uint8)
    transposedCanvas = numpy.transpose(simpleCanvas, (1, 0, 2))
    flippedColors = numpy.flip(transposedCanvas, 2)
    rawOutput = numpy.reshape(flippedColors, (canvas.shape[1], canvas.shape[0] * 3))
    return rawOutput


def getNeighborhoodColor(location, canvas, MODE):
    # if (MODE == 0):
    #     return getMinimumColorDistance(targetCoordinates, canvas)
    # elif (MODE == 1):
    #     return getAverageColorDistance(targetCoordinates, canvas)
    # elif (MODE == 2):
    #     return getAverageColor(targetCoordinates, canvas)
    # else:
    #     return getAverageColor(targetCoordinates, canvas)
    return getAverageColor(location, canvas)


# Gives all valid locations surrounding a given location
# A location is invalid only if it is outside the given canvas bonuds
def getNeighbors(canvas, targetCoordinates):

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
            neighbor = numpy.array([(targetCoordinates[0] - 1 + i), (targetCoordinates[1] - 1 + j)], numpy.uint32)

            # neighbor must be in the canvas
            neighborIsInCanvas = ((0 <= neighbor[0] < canvas.shape[0]) and (0 <= neighbor[1] < canvas.shape[1]))
            if (neighborIsInCanvas):
                neighbors[index] = neighbor
                index += 1

    # if there are any valid, neighbors return them
    if (index):
        return neighbors[0:index]
    else:
        return numpy.array([])


# filters out colored locations from a given neighbor list
# i.e. neighbor color == BLACK
def removeColoredNeighbors(neighbors, canvas):

    # Setup
    index = 0
    filteredNeighbors = numpy.zeros([8, 2], numpy.uint32)

    # KEEP only NEIGHBORS that are NOT COLORED (color equal BLACK)
    for neighbor in neighbors:

        if (isLocationBlack(neighbor, canvas)):
            filteredNeighbors[index] = neighbor
            index += 1

    # return the filtered neighbors or an empty list
    if (index):
        return filteredNeighbors[0:index]
    else:
        return numpy.array([])


def getNotPrevAvailNeighbors(targetCoordinates, canvas):

    # Setup
    index = 0
    prevAvail = False
    NotPrevAvailNeighbors = numpy.zeros([8, 2], numpy.uint32)

    consideredNeighbors = removeColoredNeighbors(getNeighbors(canvas, targetCoordinates), canvas)
    for neighbor in consideredNeighbors:
        prevAvail = False
        for neighborOfNeighbor in getNeighbors(canvas, neighbor):
            if (not isLocationBlack(neighborOfNeighbor, canvas)):
                prevAvail = True

        if (not prevAvail):
            NotPrevAvailNeighbors[index] = neighbor
            index += 1

    if (index):
        return NotPrevAvailNeighbors[0:index]
    else:
        return numpy.array([])

# filters out non-colored locations from a given neighbor list
# i.e. neighbor color =/= BLACK


def removeNonColoredNeighbors(neighbors, canvas):

    # Setup
    index = 0
    filteredNeighbors = numpy.zeros([8, 2], numpy.uint32)

    # Keep only NEIGHBORS that are COLORED (color not equal BLACK)
    for neighbor in neighbors:

        if not (isLocationBlack(neighbor, canvas)):
            filteredNeighbors[index] = neighbor
            index += 1

    # return the filtered neighbors or an empty list
    if (index):
        return filteredNeighbors[0:index]
    else:
        return numpy.array([])


# neighbor filter helper
def isLocationBlack(location, canvas):
    return numpy.array_equal(canvas[location[0], location[1]], BLACK)


# get the average color of a given location
def getAverageColor(target, canvas):
    # Setup
    index = 0
    neigborhoodColor = BLACK

    # Get neighbors
    # Don't consider BLACK pixels
    consideredNeighbors = removeNonColoredNeighbors(getNeighbors(canvas, target), canvas)

    # sum up the color values from each neighbor
    for neighbor in consideredNeighbors:
        neigborhoodColor = numpy.add(canvas[neighbor[0], neighbor[1]], neigborhoodColor)
        index += 1

    # check if the considered pixel has at least one valid neighbor
    if (index):

        # divide through by the index to average the color
        indexArray = numpy.array([index, index, index], numpy.uint32)
        avgColor = numpy.divide(neigborhoodColor, indexArray)
        roundedAvg = numpy.array(avgColor, numpy.uint32)

        return roundedAvg
    else:
        return BLACK


def getNewBoundaryNeighbors(targetCoord, canvas):
    return removeColoredNeighbors(getNeighbors(canvas, targetCoord), canvas)
