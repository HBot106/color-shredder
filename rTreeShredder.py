import png as pypng
import numpy
import rtree

import os
import sys
import time

import colorTools
import canvasTools
import config

# =============================================================================
# MACROS
# =============================================================================
COLOR_BLACK = numpy.array([0, 0, 0], numpy.uint32)
COORDINATE_INVALID = numpy.array([-1, -1])
MAX_CHANNEL_VALUE = 2**config.PARSED_ARGS.c

# =============================================================================
# GLOBALS
# =============================================================================

# empty list of all colors to be placed and an index for tracking position in the list
list_all_colors = numpy.zeros([((2**config.PARSED_ARGS.c)**3), 3], numpy.uint32)

# empty list of all colors to be placed and an index for tracking position in the list
list_collided_colors = []
index_collided_colors = 0

# used for ongoing speed calculation
time_last_print = time.time()

# canvas and list for tracking available coordinates
canvas_availability = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.bool)
list_availabilty = []


# holds the current RGB state of the canvas
canvas_actual_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint32)

# holds the average color around each canvas location
canvas_neighborhood_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint32)

# rTree
spatial_index_of_neighborhood_color_holding_location = rtree.index.Index(properties=config.index_properties)

# writes data arrays as PNG image files
png_author = pypng.Writer(config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], greyscale=False)

# New R-Tree data structure testing for lookup of available locations
index_properties = config.index_properties
spatial_index_of_neighborhood_color_holding_location = rtree.index.Index(properties=config.index_properties)


# holds the ID/index (for the spatial index) of each canvas location
canvas_location_id = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.uint32)

# writes data arrays as PNG image files

# various counters
count_colors_taken = 0
count_collisions = 0
count_colors_placed = 0
count_available_locations = 0

# =============================================================================


def shredColors():
    # generate all colors in the color space and shuffle them
    global list_of_all_colors
    list_of_all_colors = colorTools.generateColors(config.PARSED_ARGS.c, config.DEFAULT_COLOR['MULTIPROCESSING'], config.DEFAULT_COLOR['SHUFFLE'])

    # Work
    print("Painting Canvas...")
    time_of_start = time.time()

    # draw the first color at the starting pixel
    startPainting()

    # while 2 conditions, continue painting:
    #   1) more un-colored boundry locations exist
    #   2) there are more generated colors to be placed
    while(spatial_index_of_neighborhood_color_holding_location.count([0, 0, 0, 255, 255, 255]) and (count_colors_taken < list_all_colors.shape[0])):
        continuePainting()

    time_elapsed = time.time() - time_of_start

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(time_elapsed / 60) + " minutes!")

# start the painting, by placing the first target color


def startPainting():

    # Setup
    coordinate_start_point = numpy.array([config.PARSED_ARGS.s[0], config.PARSED_ARGS.s[1]], numpy.uint32)

    # get the starting color
    global count_colors_taken
    rgb_target_color = list_of_all_colors[count_colors_taken]
    count_colors_taken += 1

    # draw the first color at the starting location
    global canvas_actual_color
    global count_colors_placed
    canvas_actual_color[coordinate_start_point[0], coordinate_start_point[1]] = rgb_target_color
    count_colors_placed += 1

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((coordinate_start_point[0] - 1 + i), (coordinate_start_point[1] - 1 + j))

            # neighbor must be in the canvas
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must also be black (not already colored)
                bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if (bool_neighbor_is_black):
                    trackNeighbor(coordinate_neighbor)
    # finish first pixel
    printCurrentCanvas(True)


# continue the painting
def continuePainting():

    # get the color to be placed
    global count_colors_taken
    rgb_target_color = list_of_all_colors[count_colors_taken]
    count_colors_taken += 1

    # find the best location for that color
    coordinate_best_position = getBestPositionForColor(rgb_target_color)

    # attempt to paint the color at the corresponding location
    paintToCanvas(rgb_target_color, coordinate_best_position)


def getBestPositionForColor(rgb_requested_color):

    return list(spatial_index_of_neighborhood_color_holding_location.nearest(getColorBoundingBox(rgb_requested_color), 1, objects='RAW'))


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(rgb_requested_color, knn_querry_result_list):

    # Setup
    # nearest_neighbor = knn_querry_result_list[0]
    coordinate_nearest_neighbor = knn_querry_result_list[0].object

    # double check the the pixel is available
    if (numpy.array_equal(canvas_actual_color[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]], COLOR_BLACK)):

        # the best position for rgb_requested_color has been found color it
        canvas_actual_color[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = rgb_requested_color

        unTrackNeighbor(knn_querry_result_list[0])

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                coordinate_neighbor = ((coordinate_nearest_neighbor[0] - 1 + i), (coordinate_nearest_neighbor[1] - 1 + j))

                # neighbor must be in the canvas
                bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
                if (bool_neighbor_in_canvas):

                    # neighbor must also be black (not already colored)
                    bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                    if (bool_neighbor_is_black):
                        trackNeighbor(coordinate_neighbor)

        # print progress
        if (config.PARSED_ARGS.r):
            if (count_colors_placed % config.PARSED_ARGS.r == 0):
                printCurrentCanvas()

        return

    # major collision
    global count_collisions
    count_collisions += 1


# Track the given neighbor as available
#   if the location is already tracked, un-track it first, then re-track it.
#   this prevents duplicate availble locations, and updates the neighborhood color
# Tracking consists of:
#   inserting a new nearest_neighbor into the spatial_index_of_neighborhood_color_holding_location,
#   and flagging the associated location in the availabilityIndex
def trackNeighbor(location):

    # Globals
    global spatial_index_of_neighborhood_color_holding_location
    global canvas_location_id
    global canvas_availability
    global canvas_neighborhood_color
    global count_available_locations

    # if the neighbor is already in the spatial_index_of_neighborhood_color_holding_location, then it needs to be deleted
    # otherwise there will be duplicate avialability with outdated neighborhood colors.
    if (canvas_availability[location[0], location[1]]):
        neighborID = canvas_location_id[location[0], location[1]]
        rgb_neighborhood_color = canvas_neighborhood_color[location[0], location[1]]
        spatial_index_of_neighborhood_color_holding_location.delete(neighborID, getColorBoundingBox(rgb_neighborhood_color))

        # flag the location as no longer being available
        canvas_availability[location[0], location[1]] = False

    # get the newest neighborhood color
    rgb_neighborhood_color = getAverageColor(location)

    # update the location in the availability index
    canvas_availability[location[0]][location[1]] = True
    canvas_location_id[location[0]][location[1]] = count_available_locations
    canvas_neighborhood_color[location[0]][location[1]] = rgb_neighborhood_color

    # add the location to the spatial_index_of_neighborhood_color_holding_location
    spatial_index_of_neighborhood_color_holding_location.insert(count_available_locations, getColorBoundingBox(rgb_neighborhood_color), location)
    count_available_locations += 1


# Un-Track the given nearest_neighbor
# Un-Tracking Consists of:
#   removing the given nearest_neighbor from the spatial_index_of_neighborhood_color_holding_location,
#   and Un-Flagging the associated location in the availabilityIndex
def unTrackNeighbor(nearest_neighbor):

    locationID = nearest_neighbor.id
    coordinate_nearest_neighbor = nearest_neighbor.object
    bbox_neighborhood_color = nearest_neighbor.bbox

    # remove object from the spatial_index_of_neighborhood_color_holding_location
    global count_colors_placed
    spatial_index_of_neighborhood_color_holding_location.delete(locationID, bbox_neighborhood_color)
    count_colors_placed += 1

    # flag the location as no longer being available
    canvas_availability[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = False


# prints the current state of canvas_actual_color as well as progress stats
def printCurrentCanvas(finalize=False):

    if (config.PARSED_ARGS.r == 0) and not (finalize):
        return

    # Global Access
    global time_last_print
    global png_author

    # get time_elapsed time
    time_current = time.time()
    time_elapsed = time_current - time_last_print

    # exclude duplicate printings
    if (time_elapsed > 0):
        painting_rate = config.PARSED_ARGS.r/time_elapsed

        # write the png file
        painting_output_name = (config.PARSED_ARGS.f + '.png')
        painting_output_file = open(painting_output_name, 'wb')
        png_author.write(painting_output_file, toRawOutput(canvas_actual_color))
        painting_output_file.close()

        # Info Print
        time_last_print = time_current
        info_print = "Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec."
        print(info_print.format(count_colors_placed, spatial_index_of_neighborhood_color_holding_location.count([0, 0, 0, 255, 255, 255]), (count_colors_placed * 100 / config.PARSED_ARGS.d[0] / config.PARSED_ARGS.d[1]), count_collisions, painting_rate), end='\n')

    # if debug flag set, slow down the painting process
    if (config.DEFAULT_PAINTER['DEBUG_WAIT']):
        time.sleep(config.DEFAULT_PAINTER['DEBUG_WAIT_TIME'])


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):

    # converts the given canvas into a format that the PNG module can use to write a png
    canvas_8bit = numpy.array(canvas, numpy.uint8)
    canvas_transposed = numpy.transpose(canvas_8bit, (1, 0, 2))
    canvas_flipped = numpy.flip(canvas_transposed, 2)
    return numpy.reshape(canvas_flipped, (canvas.shape[1], canvas.shape[0] * 3))


# # prints the current state of canvas_actual_color as well as progress stats
# def printCurrentCanvas(finalize=False):

#     # Global Access
#     global time_of_last_print

#     # get time_elapsed time
#     time_current = time.time()
#     time_elapsed = time_current - time_of_last_print

#     # exclude duplicate printings
#     if (time_elapsed > 0):
#         painting_rate = PRINT_RATE/time_elapsed

#         # cancel (probably a duplicate)
#         if (painting_rate > 1000) and not (finalize):
#             return

#         # write the png file
#         output_file_name = (FILENAME + '.png')
#         output_file = open(output_file_name, 'wb')
#         png_painter.write(output_file, canvasTools.toRawOutput(canvas_actual_color))
#         output_file.close()

#         # Info Print
#         time_of_last_print = time_current
#         print("Colored: {}. Available: {}. Complete: {:3.2f}. Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
#             count_colors_placed, spatial_index_of_neighborhood_color_holding_location.count([0, 0, 0, 255, 255, 255]), (count_colors_placed * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), count_collisions, painting_rate), end='\n')


# get the average color of a given location
def getAverageColor(target):
    # Setup
    index = 0
    color_sum = COLOR_BLACK

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((target[0] - 1 + i), (target[1] - 1 + j))

            # neighbor must be in the canvas
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must not be black
                bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if not (bool_neighbor_is_black):
                    color_sum = numpy.add(color_sum, canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]])
                    index += 1

    if (index):
        color_sum = numpy.array([color_sum[0]/index, color_sum[1]/index, color_sum[2]/index])
        return color_sum
    else:

        return COLOR_BLACK


# turn a given color into its bounding box representation
# numpy[r,g,b] -> (r,r,g,g,b,b)
def getColorBoundingBox(rgb_requested_color):
    if (rgb_requested_color.size == 3):
        return (rgb_requested_color[0], rgb_requested_color[1], rgb_requested_color[2], rgb_requested_color[0], rgb_requested_color[1], rgb_requested_color[2])
    else:
        print("getColorBoundingBox given bad value")
        print("given:")
        print(rgb_requested_color)
        quit()
