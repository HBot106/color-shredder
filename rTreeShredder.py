import png as pypng
import numpy
from rtree import index as rTree

import os
import sys
import time

import colorTools
import canvasTools
import config


# =============================================================================
# MACROS
# =============================================================================
# output_file_name of the output PNG file
FILENAME = config.PARSED_ARGS.f

# color selection mode
MODE = config.PARSED_ARGS.q

# color generation settings
SHUFFLE_COLORS = config.DEFAULT_COLOR['SHUFFLE']
USE_MULTIPROCESSING = config.DEFAULT_COLOR['MULTIPROCESSING']

# painter settings
PRINT_RATE = config.PARSED_ARGS.r
LOCATIONS_PER_PAINTER = config.DEFAULT_PAINTER['LOCATIONS_PER_PAINTER']
MIN_MULTI_WORKLOAD = config.DEFAULT_PAINTER['MIN_MULTI_WORKLOAD']
MAX_PAINTERS = os.cpu_count() * 2

# canvas settings
COLOR_BIT_DEPTH = config.PARSED_ARGS.c
TOTAL_NUMBER_OF_COLORS = ((2**COLOR_BIT_DEPTH)**3)
CANVAS_SIZE = numpy.array([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.uint32)
START_POINT = numpy.array([config.PARSED_ARGS.s[0], config.PARSED_ARGS.s[1]], numpy.uint32)

# special values
BLACK = numpy.array([0, 0, 0], numpy.uint32)
INVALID_COORD = numpy.array([-1, -1], numpy.int8)

# =============================================================================
# GLOBALS
# =============================================================================
# list of all colors to be placed
list_of_all_colors = numpy.zeros([TOTAL_NUMBER_OF_COLORS, 3], numpy.uint32)

# used for ongoing speed calculation
time_of_last_print = time.time()

# New R-Tree data structure testing for lookup of available locations
index_properties = config.index_properties
spatial_index_of_neighborhood_color_holding_location = rTree.Index(properties=config.index_properties)

# CANVASES
# Canvases are 2d arrays that are the size of the output painting
#
# holds boolean availability for each canvas location
canvas_location_availability = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.bool)
# holds the ID/index (for the spatial index) of each canvas location
canvas_location_id = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.uint32)
# holds the current state of the painting
canvas_actual_color = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)
# holds the average color around each canvas location
canvas_neighborhood_color = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# writes data arrays as PNG image files
png_painter = pypng.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

# various counters
count_colors_taken = 0
count_collisions = 0
count_colors_placed = 0
count_available_locations = 0


# =============================================================================
def shredColors():
    # generate all colors in the color space and shuffle them
    global list_of_all_colors
    list_of_all_colors = colorTools.generateColors(COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    time_of_start = time.time()

    # draw the first color at the starting pixel
    startPainting()

    # while 2 conditions, continue painting:
    #   1) more un-colored boundry locations exist
    #   2) there are more generated colors to be placed
    while(spatial_index_of_neighborhood_color_holding_location.count([0, 0, 0, 256, 256, 256]) and (count_colors_taken < TOTAL_NUMBER_OF_COLORS)):
        continuePainting()

    time_elapsed = time.time() - time_of_start

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(time_elapsed / 60) + " minutes!")


# start the painting, by placing the first target color
def startPainting():

    # Setup
    coordinate_start_point = numpy.array([START_POINT[0], START_POINT[1]], numpy.uint32)

    # get the starting color
    global count_colors_taken
    rgb_target_color = list_of_all_colors[count_colors_taken]
    count_colors_taken += 1

    # draw the first color at the starting location
    global canvas_actual_color
    global count_colors_placed
    canvas_actual_color[coordinate_start_point[0], coordinate_start_point[1]] = rgb_target_color
    count_colors_placed += 1

    # add its neigbors to uncolored Boundary Region
    for neighbor in canvasTools.getNewBoundaryNeighbors(coordinate_start_point, canvas_actual_color):

        trackNeighbor(neighbor)

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
    return list(spatial_index_of_neighborhood_color_holding_location.nearest(colorTools.getColorBoundingBox(rgb_requested_color), 1, objects='RAW'))


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(rgb_requested_color, knn_querry_result_list):

    # Setup
    # nearest_neighbor = knn_querry_result_list[0]
    coordinate_nearest_neighbor = knn_querry_result_list[0].object

    # double check the the pixel is available
    if (canvasTools.isLocationBlack(coordinate_nearest_neighbor, canvas_actual_color)):

        # the best position for rgb_requested_color has been found color it
        canvas_actual_color[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = rgb_requested_color

        unTrackNeighbor(knn_querry_result_list[0])

        # each valid neighbor position should be added to uncolored Boundary Region
        for neighbor in canvasTools.getNewBoundaryNeighbors(coordinate_nearest_neighbor, canvas_actual_color):

            trackNeighbor(neighbor)

        # print progress
        if (count_colors_placed % PRINT_RATE == 0):
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
    global canvas_location_availability
    global canvas_neighborhood_color
    global count_available_locations

    # if the neighbor is already in the spatial_index_of_neighborhood_color_holding_location, then it needs to be deleted
    # otherwise there will be duplicate avialability with outdated neighborhood colors.
    if (canvas_location_availability[location[0], location[1]]):
        neighborID = canvas_location_id[location[0], location[1]]
        rgb_neighborhood_color = canvas_neighborhood_color[location[0], location[1]]
        spatial_index_of_neighborhood_color_holding_location.delete(neighborID, colorTools.getColorBoundingBox(rgb_neighborhood_color))

        # flag the location as no longer being available
        canvas_location_availability[location[0], location[1]] = False

    # get the newest neighborhood color
    rgb_neighborhood_color = canvasTools.getAverageColor(location, canvas_actual_color)

    # update the location in the availability index
    canvas_location_availability[location[0]][location[1]] = True
    canvas_location_id[location[0]][location[1]] = count_available_locations
    canvas_neighborhood_color[location[0]][location[1]] = rgb_neighborhood_color

    # add the location to the spatial_index_of_neighborhood_color_holding_location
    spatial_index_of_neighborhood_color_holding_location.insert(count_available_locations, colorTools.getColorBoundingBox(rgb_neighborhood_color), location)
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
    canvas_location_availability[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = False


# prints the current state of canvas_actual_color as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global time_of_last_print

    # get time_elapsed time
    time_current = time.time()
    time_elapsed = time_current - time_of_last_print

    # exclude duplicate printings
    if (time_elapsed > 0):
        painting_rate = PRINT_RATE/time_elapsed

        # cancel (probably a duplicate)
        if (painting_rate > 1000) and not (finalize):
            return

        # write the png file
        output_file_name = (FILENAME + '.png')
        output_file = open(output_file_name, 'wb')
        png_painter.write(output_file, canvasTools.toRawOutput(canvas_actual_color))
        output_file.close()

        # Info Print
        time_of_last_print = time_current
        print("Colored: {}. Available: {}. Complete: {:3.2f}. Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            count_colors_placed, spatial_index_of_neighborhood_color_holding_location.count([0, 0, 0, 256, 256, 256]), (count_colors_placed * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), count_collisions, painting_rate), end='\n')
