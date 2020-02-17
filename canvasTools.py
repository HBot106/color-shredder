import colorTools

import sys
import numpy

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# converts a canvas_actual_color into raw data for writing to a png
def toRawOutput(canvas_actual_color):

    # converts the given canvas_actual_color into a format that the PNG module can use to write a png
    raw_canvas = numpy.array(canvas_actual_color, numpy.uint8)
    transposed_canvas = numpy.transpose(raw_canvas, (1, 0, 2))
    flipped_transposed_canvas = numpy.flip(transposed_canvas, 2)
    output_canvas = numpy.reshape(flipped_transposed_canvas, (canvas_actual_color.shape[1], canvas_actual_color.shape[0] * 3))
    return output_canvas


# Gives all valid locations surrounding a given location
# A location is invalid only if it is outside the given canvas_actual_color bonuds
def getNeighbors(canvas_actual_color, coordinate_target_location):

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
            neighbor = numpy.array([(coordinate_target_location[0] - 1 + i), (coordinate_target_location[1] - 1 + j)], numpy.uint32)

            # neighbor must be in the canvas_actual_color
            is_neighbor_on_canvas = ((0 <= neighbor[0] < canvas_actual_color.shape[0]) and (0 <= neighbor[1] < canvas_actual_color.shape[1]))
            if (is_neighbor_on_canvas):
                neighbors[index] = neighbor
                index += 1

    # if there are any valid, neighbors return them
    if (index):
        return neighbors[0:index]
    else:
        return numpy.array([])


# filters out colored locations from a given neighbor list
# i.e. neighbor color == BLACK
def removeColoredNeighbors(neighbors, canvas_actual_color):

    # Setup
    index = 0
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # KEEP only NEIGHBORS that are NOT COLORED (color equal BLACK)
    for neighbor in neighbors:

        if (isLocationBlack(neighbor, canvas_actual_color)):
            list_of_filtered_neighbors[index] = neighbor
            index += 1

    # return the filtered neighbors or an empty list
    if (index):
        return list_of_filtered_neighbors[0:index]
    else:
        return numpy.array([])


def getNotPrevAvailNeighbors(coordinate_target_location, canvas_actual_color):

    # Setup
    index = 0
    was_previously_available = False
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Get neighbors
    # Don't consider BLACK pixels
    list_of_pre_filtered_neighbors = removeColoredNeighbors(getNeighbors(canvas_actual_color, coordinate_target_location), canvas_actual_color)
    
    for neighbor in list_of_pre_filtered_neighbors:
        was_previously_available = False
        for neighbor_of_neighbor in getNeighbors(canvas_actual_color, neighbor):
            if (not isLocationBlack(neighbor_of_neighbor, canvas_actual_color)):
                was_previously_available = True

        if (not was_previously_available):
            list_of_filtered_neighbors[index] = neighbor
            index += 1

    if (index):
        return list_of_filtered_neighbors[0:index]
    else:
        return numpy.array([])


# filters out non-colored locations from a given neighbor list
# i.e. neighbor color =/= BLACK
def removeNonColoredNeighbors(neighbors, canvas_actual_color):

    # Setup
    index = 0
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Keep only NEIGHBORS that are COLORED (color not equal BLACK)
    for neighbor in neighbors:

        if not (isLocationBlack(neighbor, canvas_actual_color)):
            list_of_filtered_neighbors[index] = neighbor
            index += 1

    # return the filtered neighbors or an empty list
    if (index):
        return list_of_filtered_neighbors[0:index]
    else:
        return numpy.array([])


# neighbor filter helper
def isLocationBlack(location, canvas_actual_color):
    return numpy.array_equal(canvas_actual_color[location[0], location[1]], BLACK)


# get the average color of a given location
def getAverageColor(target, canvas_actual_color):
    # Setup
    index = 0
    rgb_color_sum = BLACK

    # Get neighbors
    # Don't consider BLACK pixels
    list_of_pre_filtered_neighbors = removeNonColoredNeighbors(getNeighbors(canvas_actual_color, target), canvas_actual_color)

    # sum up the color values from each neighbor
    for neighbor in list_of_pre_filtered_neighbors:
        rgb_color_sum = numpy.add(canvas_actual_color[neighbor[0], neighbor[1]], rgb_color_sum)
        index += 1

    # check if the considered pixel has at least one valid neighbor
    if (index):

        # divide through by the index to average the color
        rgb_divisor_array = numpy.array([index, index, index], numpy.uint32)
        rgb_average_color = numpy.divide(rgb_color_sum, rgb_divisor_array)
        rgb_average_color_rounded = numpy.array(rgb_average_color, numpy.uint32)

        return rgb_average_color_rounded
    else:
        return BLACK


def getNewBoundaryNeighbors(targetCoord, canvas_actual_color):
    return removeColoredNeighbors(getNeighbors(canvas_actual_color, targetCoord), canvas_actual_color)
