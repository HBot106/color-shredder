import png
import numpy
import numba
import rtree

import sys
import concurrent.futures
import time

import colorTools
import canvasTools
import config

# =============================================================================
# MACROS
# =============================================================================
COLOR_BLACK = numpy.array([0, 0, 0], numpy.uint32)
COORDINATE_INVALID = numpy.array([-1, -1], numpy.int8)

# =============================================================================
# GLOBALS
# =============================================================================

# list of all colors to be placed
list_all_colors = numpy.zeros([((2**config.PARSED_ARGS.c)**3), 3], numpy.uint32)
index_all_colors = 0
# empty list of all colors to be placed and an index for tracking position in the list
list_collided_colors = []
index_collided_colors = 0

# R-Tree data structure testing for lookup of available locations
rTree_neighborhood_colors = rtree.index.Index(properties=config.index_properties)

# CANVASES
# Canvases are 2d arrays that are the size of the output painting
#
# holds boolean availability for each canvas location
canvas_availability = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.bool)
list_availabilty = []
# holds the ID/index (for the spatial index) of each canvas location
canvas_id = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.uint32)
# holds the current state of the painting
canvas_actual_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint32)
# holds the average color around each canvas location
canvas_neighborhood_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint32)

# writes data arrays as PNG image files
png_painter = png.Writer(config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], greyscale=False)
# used for ongoing speed calculation
time_last_print = time.time()
# counters
count_collisions = 0
count_colors_placed = 0
count_available = 0
# =============================================================================


def shredColors():
    # generate all colors in the color space and shuffle them
    global list_all_colors
    list_all_colors = colorTools.generateColors(config.PARSED_ARGS.c, config.DEFAULT_COLOR['MULTIPROCESSING'], config.DEFAULT_COLOR['SHUFFLE'])

    # Work
    print("Painting Canvas...")
    time_of_start = time.time()

    # draw the first color at the starting pixel
    startPainting()

    # while 2 conditions, continue painting:
    #   1) more un-colored boundry locations exist
    #   2) there are more generated colors to be placed
    while(rTree_neighborhood_colors.count([0, 0, 0, 256, 256, 256]) and (index_all_colors < len(list_all_colors))):
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
    global index_all_colors
    rgb_target_color = list_all_colors[index_all_colors]
    index_all_colors += 1

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
    global index_all_colors
    rgb_target_color = list_all_colors[index_all_colors]
    index_all_colors += 1

    # find the best location for that color
    coordinate_best_position = getBestPositionForColor(rgb_target_color)

    # attempt to paint the color at the corresponding location
    paintToCanvas(rgb_target_color, coordinate_best_position)


def getBestPositionForColor(rgb_requested_color):
    return list(rTree_neighborhood_colors.nearest(colorTools.getColorBoundingBox(rgb_requested_color), 1, objects='RAW'))


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

        # each valid neighbor position should be added to uncolored Boundary Region
        for neighbor in canvasTools.getNewBoundaryNeighbors(coordinate_nearest_neighbor, canvas_actual_color):

            trackNeighbor(neighbor)

        # print progress
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
#   inserting a new nearest_neighbor into the rTree_neighborhood_colors,
#   and flagging the associated location in the availabilityIndex
def trackNeighbor(location):

    # Globals
    global rTree_neighborhood_colors
    global canvas_id
    global canvas_availability
    global canvas_neighborhood_color
    global count_available

    # if the neighbor is already in the rTree_neighborhood_colors, then it needs to be deleted
    # otherwise there will be duplicate avialability with outdated neighborhood colors.
    if (canvas_availability[location[0], location[1]]):
        neighborID = canvas_id[location[0], location[1]]
        rgb_neighborhood_color = canvas_neighborhood_color[location[0], location[1]]
        rTree_neighborhood_colors.delete(neighborID, colorTools.getColorBoundingBox(rgb_neighborhood_color))

        # flag the location as no longer being available
        canvas_availability[location[0], location[1]] = False

    # get the newest neighborhood color
    rgb_neighborhood_color = canvasTools.getAverageColor(location, canvas_actual_color)

    # update the location in the availability index
    canvas_availability[location[0]][location[1]] = True
    canvas_id[location[0]][location[1]] = count_available
    canvas_neighborhood_color[location[0]][location[1]] = rgb_neighborhood_color

    # add the location to the rTree_neighborhood_colors
    rTree_neighborhood_colors.insert(count_available, colorTools.getColorBoundingBox(rgb_neighborhood_color), location)
    count_available += 1


# Un-Track the given nearest_neighbor
# Un-Tracking Consists of:
#   removing the given nearest_neighbor from the rTree_neighborhood_colors,
#   and Un-Flagging the associated location in the availabilityIndex
def unTrackNeighbor(nearest_neighbor):

    locationID = nearest_neighbor.id
    coordinate_nearest_neighbor = nearest_neighbor.object
    bbox_neighborhood_color = nearest_neighbor.bbox

    # remove object from the rTree_neighborhood_colors
    global count_colors_placed
    rTree_neighborhood_colors.delete(locationID, bbox_neighborhood_color)
    count_colors_placed += 1

    # flag the location as no longer being available
    canvas_availability[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = False


# prints the current state of canvas_actual_color as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global time_last_print

    # get time_elapsed time
    time_current = time.time()
    time_elapsed = time_current - time_last_print

    # exclude duplicate printings
    if (time_elapsed > 0):
        painting_rate = config.PARSED_ARGS.r/time_elapsed

        # cancel (probably a duplicate)
        if (painting_rate > 1000) and not (finalize):
            return

        # write the png file
        output_file_name = (config.PARSED_ARGS.f + '.png')
        output_file = open(output_file_name, 'wb')
        png_painter.write(output_file, getRawOutput())
        output_file.close()

        # Info Print
        time_last_print = time_current
        print("Colored: {}. Available: {}. Complete: {:3.2f}. Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            count_colors_placed, rTree_neighborhood_colors.count([0, 0, 0, 256, 256, 256]), (count_colors_placed * 100 / config.PARSED_ARGS.d[0] / config.PARSED_ARGS.d[1]), count_collisions, painting_rate), end='\n')


# converts a canvas into raw data for writing to a png
def getRawOutput():

    # converts the given canvas into a format that the PNG module can use to write a png
    canvas_8bit = numpy.array(canvas_actual_color, numpy.uint8)
    canvas_transposed = numpy.transpose(canvas_8bit, (1, 0, 2))
    canvas_flipped = numpy.flip(canvas_transposed, 2)
    return numpy.reshape(canvas_flipped, (canvas_actual_color.shape[1], canvas_actual_color.shape[0] * 3))

    