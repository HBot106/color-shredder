import colorTools
import numpy

# BLACK reference
# BLACK = [0, 0, 0]
BLACK = numpy.zeros(3, numpy.uint8)


# takes the canvas (2d color list) and converts it to
# the format [[r,g,b,r,g,b...],[r,g,b,r,g,b...]...]
# for later writing to a png
def toRawOutput(canvas):
    # rawOutput = []
    # height = len(canvas)
    # width = len(canvas[0])

    # for y in range(width):
    #     rowOutput = []
    #     for x in range(height):
    #         rowOutput += getColorAt(canvas, [x, y])
    #     rawOutput.append(rowOutput)
    # return rawOutput

    return canvas.transpose(1, 0, 2).reshape(-1, canvas[0].size)


def constructBlank(width, height):
    # canvas = []

    # # loop over the whole canvas, adding sub-lists of BLACK color objects to a super-list
    # for _ in range(width):
    #     column = []
    #     for _ in range(height):
    #         column.append(BLACK)
    #     canvas.append(column)

    # return canvas

    return (numpy.zeros([width, height, 3], numpy.uint8))


# set the color at a position in the canvas
def setColorAt(canvas, color, coord):
    canvas[coord[0], coord[1]] = color


# get the color at a position in the canvas
def getColorAt(canvas, coord):
    return canvas[coord[0], coord[1]]


def considerPixelAt(canvas, coord, targetColor, useAverage):
    neighborDifferences = []
    width = canvas.size
    height = canvas[0].size

    # loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            neighbor = [coord[0] - 1 + i,
                        coord[1] - 1 + j]

            # if they are within the canvas add them to the final neigbor list
            if (0 <= neighbor[0] < width) and (0 <= neighbor[1] < height) and not (canvas[neighbor[0], neighbor[1]].all() == BLACK).all():
                considerColor = canvas[neighbor[0], neighbor[1]]
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


def getValidNeighbors(canvas, coord):
    neighbors = []
    width = len(canvas)
    height = len(canvas[0])

    # loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            neighbor = [coord[0] - 1 + i,
                        coord[1] - 1 + j]

            # if they are within the canvas add them to the final neigbor list
            if (0 <= neighbor[0] < width) and (0 <= neighbor[1] < height) and (canvas[neighbor[0], neighbor[1]].all() == BLACK.all()):
                neighbors.append(neighbor)

    return neighbors
