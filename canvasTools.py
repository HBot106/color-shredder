import colorTools
import config

import sys
import numpy

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# converts a canvas_actual_color into raw data for writing to a png
# @njit
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
    index_of_neighbor = 0
    list_of_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_of_neighbor = numpy.array([(coordinate_target_location[0] - 1 + i), (coordinate_target_location[1] - 1 + j)], numpy.uint32)

            # coordinate_of_neighbor must be in the canvas_actual_color
            is_neighbor_on_canvas = ((0 <= coordinate_of_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_of_neighbor[1] < canvas_actual_color.shape[1]))
            if (is_neighbor_on_canvas):
                list_of_neighbors[index_of_neighbor] = coordinate_of_neighbor
                index_of_neighbor += 1

    # if there are any valid, list_of_neighbors return them
    if (index_of_neighbor):
        return list_of_neighbors[0:index_of_neighbor]
    else:
        return numpy.array([])


# filters out colored locations from a given coordinate_of_neighbor list
# i.e. coordinate_of_neighbor color == BLACK
def removeColoredNeighbors(list_of_neighbors, canvas_actual_color):

    # Setup
    index_of_neighbor = 0
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # KEEP only list_of_neighbors that are NOT COLORED (color equal BLACK)
    for coordinate_of_neighbor in list_of_neighbors:

        if (isLocationBlack(coordinate_of_neighbor, canvas_actual_color)):
            list_of_filtered_neighbors[index_of_neighbor] = coordinate_of_neighbor
            index_of_neighbor += 1

    # return the filtered list_of_neighbors or an empty list
    if (index_of_neighbor):
        return list_of_filtered_neighbors[0:index_of_neighbor]
    else:
        return numpy.array([])


def getNotPrevAvailNeighbors(coordinate_target_location, canvas_actual_color):

    # Setup
    index_of_neighbor = 0
    was_previously_available = False
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Get list_of_neighbors
    # Don't consider BLACK pixels
    list_of_pre_filtered_neighbors = removeColoredNeighbors(getNeighbors(canvas_actual_color, coordinate_target_location), canvas_actual_color)
    
    for coordinate_of_neighbor in list_of_pre_filtered_neighbors:
        was_previously_available = False
        for neighbor_of_neighbor in getNeighbors(canvas_actual_color, coordinate_of_neighbor):
            if (not isLocationBlack(neighbor_of_neighbor, canvas_actual_color)):
                was_previously_available = True

        if (not was_previously_available):
            list_of_filtered_neighbors[index_of_neighbor] = coordinate_of_neighbor
            index_of_neighbor += 1

    if (index_of_neighbor):
        return list_of_filtered_neighbors[0:index_of_neighbor]
    else:
        return numpy.array([])


# filters out non-colored locations from a given coordinate_of_neighbor list
# i.e. coordinate_of_neighbor color =/= BLACK
def removeNonColoredNeighbors(list_of_neighbors, canvas_actual_color):

    # Setup
    index_of_neighbor = 0
    list_of_filtered_neighbors = numpy.zeros([8, 2], numpy.uint32)

    # Keep only list_of_neighbors that are COLORED (color not equal BLACK)
    for coordinate_of_neighbor in list_of_neighbors:

        if not (isLocationBlack(coordinate_of_neighbor, canvas_actual_color)):
            list_of_filtered_neighbors[index_of_neighbor] = coordinate_of_neighbor
            index_of_neighbor += 1

    # return the filtered list_of_neighbors or an empty list
    if (index_of_neighbor):
        return list_of_filtered_neighbors[0:index_of_neighbor]
    else:
        return numpy.array([])


# coordinate_of_neighbor filter helper
def isLocationBlack(location, canvas_actual_color):
    return numpy.array_equal(canvas_actual_color[location[0], location[1]], BLACK)


# get the average color of a given location
def getAverageColor(target, canvas_actual_color):
    # Setup
    index_of_neighbor = 0
    rgb_color_sum = BLACK

    # Get list_of_neighbors
    # Don't consider BLACK pixels
    list_of_pre_filtered_neighbors = removeNonColoredNeighbors(getNeighbors(canvas_actual_color, target), canvas_actual_color)

    # sum up the color values from each coordinate_of_neighbor
    for coordinate_of_neighbor in list_of_pre_filtered_neighbors:
        rgb_color_sum = numpy.add(canvas_actual_color[coordinate_of_neighbor[0], coordinate_of_neighbor[1]], rgb_color_sum)
        index_of_neighbor += 1

    # check if the considered pixel has at least one valid coordinate_of_neighbor
    if (index_of_neighbor):

        # divide through by the index_of_neighbor to average the color
        rgb_divisor_array = numpy.array([index_of_neighbor, index_of_neighbor, index_of_neighbor], numpy.uint32)
        rgb_average_color = numpy.divide(rgb_color_sum, rgb_divisor_array)
        rgb_average_color_rounded = numpy.array(rgb_average_color, numpy.uint32)

        return rgb_average_color_rounded
    else:
        return BLACK


def getNewBoundaryNeighbors(targetCoord, canvas_actual_color):
    return removeColoredNeighbors(getNeighbors(canvas_actual_color, targetCoord), canvas_actual_color)
