# =============================================================================
# MODULES
# =============================================================================
import png
import numpy
import numba
import rtree

import sys
import concurrent.futures
import time

import colorTools
import config


# =============================================================================
# MACROS
# =============================================================================
COLOR_BLACK = numpy.array([0, 0, 0], numpy.uint64)
COORDINATE_INVALID = numpy.array([-1, -1])


# =============================================================================
# GLOBALS
# =============================================================================
# process_pool executor
mutliprocessing_painter_manager = concurrent.futures.ProcessPoolExecutor()
# list of all colors to be placed
list_all_colors = numpy.zeros([((2**config.PARSED_ARGS.c)**3), 3], numpy.uint64)
index_all_colors = 0
# empty list of all colors to be placed and an index for tracking position in the list
list_collided_colors = []
index_collided_colors = 0
# writes data arrays as PNG image files
png_painter = png.Writer(config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], greyscale=False)
# used for ongoing speed calculation
time_last_print = time.time()
# counters
count_collisions = 0
count_colors_placed = 0
count_available = 0
count_id = 0


# =============================================================================
# DATA-STRUCTURES
# =============================================================================
# R-Tree data structure testing for lookup of available locations
rTree_neighborhood_colors = rtree.index.Index(properties=config.index_properties)
# holds boolean availability for each canvas location
canvas_availability = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.bool)
list_availabilty = []
# holds the ID/index (for the spatial index) of each canvas location
canvas_id = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1]], numpy.uint64)
# holds the current state of the painting
canvas_actual_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint64)
# holds the average color around each canvas location
canvas_neighborhood_color = numpy.zeros([config.PARSED_ARGS.d[0], config.PARSED_ARGS.d[1], 3], numpy.uint64)


# =============================================================================
# COMMON
# =============================================================================
def main():
    # Global Access
    global list_all_colors
    global mutliprocessing_painter_manager

    # Setup
    list_all_colors = colorTools.generateColors()
    print("Painting Canvas...")
    time_started = time.time()

    # draw the first color at the starting pixel
    startPainting()

    # Work
    if (config.PARSED_ARGS.t):
        while(rTree_neighborhood_colors.count([0, 0, 0, 256, 256, 256]) and (index_all_colors < list_all_colors.shape[0])):
            continuePainting()
    else:
        # while more un-colored boundry locations exist and there are more colors to be placed, continue painting
        while(count_available and (index_all_colors < list_all_colors.shape[0])):
            continuePainting()

    # while more un-colored boundry locations exist and there are more collision colors to be placed, continue painting
    while(count_available and (index_collided_colors < len(list_collided_colors))):
        finishPainting()

    # Final Print Authoring
    time_elapsed = time.time() - time_started
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(time_elapsed / 60) + " minutes!")

    # teardown the process pool
    mutliprocessing_painter_manager.shutdown()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global index_all_colors

    # Setup
    color_selected = list_all_colors[index_all_colors]
    coordinate_start_point = numpy.array([config.PARSED_ARGS.s[0], config.PARSED_ARGS.s[1]])
    index_all_colors += 1

    # draw the first color at the starting pixel
    paintToCanvas(color_selected, coordinate_start_point)

    if (config.PARSED_ARGS.t):
        # add its neigbors to uncolored Boundary Region
        trackNewBoundyNeighbors_rTree(coordinate_start_point)
    else:
        # for the 8 neighboring locations check that they are in the canvas and uncolored (black), then account for their availabity
        trackNewBoundyNeighbors_bruteForce(coordinate_start_point)

    # finish first pixel
    printCurrentCanvas(True)


# continue the painting, manages multiple painters or a single painter dynamically
def continuePainting():

    # Global Access
    global index_all_colors
    global mutliprocessing_painter_manager

    # Setup
    # if more than MIN_MULTI_WORKLOAD locations are available, allow multiprocessing
    # also check for config flag
    if ((count_available > config.DEFAULT_PAINTER['MIN_MULTI_WORKLOAD']) and config.PARSED_ARGS.m):
        list_painter_work_queue = []

        # cap the number of workers so that there are at least LOCATIONS_PER_PAINTER free locations per worker
        # this keeps the number of collisions down
        # limit the total possible workers to MAX_PAINTERS (twice the CPU count) to not add unnecessary overhead
        # loop over each one
        for _ in range(min(((count_available//config.DEFAULT_PAINTER['LOCATIONS_PER_PAINTER']), config.DEFAULT_PAINTER['MAX_PAINTERS']))):

            # check that more colors are available
            if (index_all_colors < len(list_all_colors)):

                # get the color to be placed
                color_selected = list_all_colors[index_all_colors]
                index_all_colors += 1

                # schedule a worker to find the best location for that color
                list_neighbor_diffs = numpy.zeros(8, numpy.uint64)
                list_painter_work_queue.append(mutliprocessing_painter_manager.submit(getBestPositionForColor_bruteForce, color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_actual_color, config.PARSED_ARGS.q))

        # as each worker completes
        for painter_worker in concurrent.futures.as_completed(list_painter_work_queue):

            # collect the best location for that color
            worker_color_selected = painter_worker.result()[0]
            worker_corrdinate_selected = painter_worker.result()[1]

            # attempt to paint the color at the corresponding location
            paintToCanvas(worker_color_selected, worker_corrdinate_selected)

    # otherwise, use only the main process
    # This is because the overhead of multithreading makes singlethreading better for small problems
    else:
        # get the color to be placed
        color_selected = list_all_colors[index_all_colors]
        index_all_colors += 1

        if (config.PARSED_ARGS.t):
            # find the best location for that color
            coordinate_best_position = getBestPositionForColor_rTree(color_selected)
            # attempt to paint the color at the corresponding location
            paintToCanvas(color_selected, coordinate_best_position[0].object, coordinate_best_position[0])
        else:
            # find the best location for that color
            list_neighbor_diffs = numpy.zeros(8, numpy.uint64)
            coordinate_selected = getBestPositionForColor_bruteForce(color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_actual_color, config.PARSED_ARGS.q)[1]
            # attempt to paint the color at the corresponding location
            paintToCanvas(color_selected, coordinate_selected)


# finish the painting using brute force on the list of all colors that were not placed due to collisions
def finishPainting():
    global index_collided_colors

    # get the color to be placed
    color_selected = list_collided_colors[index_collided_colors]
    index_collided_colors += 1

    # find the best location for that color
    list_neighbor_diffs = numpy.zeros(8, numpy.uint64)
    coordinate_selected = getBestPositionForColor_bruteForce(color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_actual_color, config.PARSED_ARGS.q)[1]

    # attempt to paint the color at the corresponding location
    paintToCanvas(color_selected, coordinate_selected)


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requested_color, requested_coord, knn_querry_result=False):

    # Global Access
    global count_collisions
    global count_colors_placed
    global canvas_actual_color

    # double check the the pixel is available
    if (numpy.array_equal(canvas_actual_color[requested_coord[0], requested_coord[1]], COLOR_BLACK)):

        # the best position for rgb_requested_color has been found color it
        canvas_actual_color[requested_coord[0], requested_coord[1]] = requested_color
        count_colors_placed += 1

        if (knn_querry_result):
            # remove neighbor from rTree
            unTrackCoordinate_rTree(knn_querry_result)
            # each valid neighbor position should be added to uncolored Boundary Region
            trackNewBoundyNeighbors_rTree(requested_coord)

        else:
            # remove neigbor from availibility canvas
            unTrackCoordinate_bruteForce(requested_coord)
            # for the 8 neighboring locations check that they are in the canvas and uncolored (black), then account for their availabity
            trackNewBoundyNeighbors_bruteForce(requested_coord)

        # print progress
        printCurrentCanvas()

    # collision
    else:
        list_collided_colors.append(requested_color)
        count_collisions += 1


# converts a canvas into raw data for writing to a png
def getRawOutput():

    # converts the given canvas into a format that the PNG module can use to write a png
    canvas_8bit = numpy.array(canvas_actual_color, numpy.uint8)
    canvas_transposed = numpy.transpose(canvas_8bit, (1, 0, 2))
    canvas_flipped = numpy.flip(canvas_transposed, 2)
    return numpy.reshape(canvas_flipped, (canvas_actual_color.shape[1], canvas_actual_color.shape[0] * 3))


# prints the current state of canvas_actual_color as well as progress stats
def printCurrentCanvas(finalize=False):

    if (config.PARSED_ARGS.r == 0) and not (finalize):
        return

    # Global Access
    global time_last_print
    global png_painter

    if not (count_colors_placed % config.PARSED_ARGS.r):

        # get time_elapsed time
        time_current = time.time()
        time_elapsed = time_current - time_last_print

        # exclude duplicate printings
        if (time_elapsed):
            painting_rate = config.PARSED_ARGS.r/time_elapsed

            # write the png file
            painting_output_name = (config.PARSED_ARGS.f + '.png')
            painting_output_file = open(painting_output_name, 'wb')
            png_painter.write(painting_output_file, getRawOutput())
            painting_output_file.close()

            # Info Print
            time_last_print = time_current
            info_print = "Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec."
            print(info_print.format(count_colors_placed, count_available, (count_colors_placed * 100 / config.PARSED_ARGS.d[0] / config.PARSED_ARGS.d[1]), count_collisions, painting_rate), end='\n')

    if (finalize):
        # get time_elapsed time
        time_current = time.time()
        time_elapsed = time_current - time_last_print

        # exclude duplicate printings
        if (time_elapsed):
            painting_rate = config.PARSED_ARGS.r/time_elapsed

            # write the png file
            painting_output_name = (config.PARSED_ARGS.f + '.png')
            painting_output_file = open(painting_output_name, 'wb')
            png_painter.write(painting_output_file, getRawOutput())
            painting_output_file.close()

            # Info Print
            time_last_print = time_current
            info_print = "Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec."
            print(info_print.format(count_colors_placed, count_available, (count_colors_placed * 100 / config.PARSED_ARGS.d[0] / config.PARSED_ARGS.d[1]), count_collisions, painting_rate), end='\n')

    # if debug flag set, slow down the painting process
    if (config.DEFAULT_PAINTER['DEBUG_WAIT']):
        time.sleep(config.DEFAULT_PAINTER['DEBUG_WAIT_TIME'])


def getColorBoundingBox(color):
    return(color[0], color[1], color[2], color[0], color[1], color[2])


# get the average color of a given location
def getAverageColor(coordinate_requested):
    # Setup
    index_of_neighbor = 0
    rgb_color_sum = COLOR_BLACK

    # Get list_of_neighbors
    # Don't consider BLACK pixels
    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((coordinate_requested[0] - 1 + i), (coordinate_requested[1] - 1 + j))

            # neighbor must be in the canvas
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must also be black (not already colored)
                bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if not (bool_neighbor_is_black):

                    rgb_color_sum = numpy.add(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], rgb_color_sum)
                    index_of_neighbor += 1

    # check if the considered pixel has at least one valid coordinate_of_neighbor
    if (index_of_neighbor):

        # divide through by the index_of_neighbor to average the color
        rgb_divisor_array = numpy.array([index_of_neighbor, index_of_neighbor, index_of_neighbor], numpy.uint64)
        rgb_average_color = numpy.divide(rgb_color_sum, rgb_divisor_array)
        rgb_average_color_rounded = numpy.array(rgb_average_color, numpy.uint64)

        return rgb_average_color_rounded
    else:
        return COLOR_BLACK


# =============================================================================
# BRUTE_FORCE
# =============================================================================
# Gives the best location among all avilable for the requested color; Also returns the color itself
def getBestPositionForColor_bruteForce(color_selected, list_neighbor_diffs, list_available_coordinates, canvas_painting, mode_selected):

    # reset minimums
    coordinate_minumum = COORDINATE_INVALID
    distance_minumum = sys.maxsize

    # for every coordinate_available position in the boundry, perform the check, keep the best position:
    for index in range(list_available_coordinates.shape[0]):

        index_neighbor_diffs = 0
        list_neighbor_diffs.fill(0)
        color_difference = [0, 0, 0]
        color_difference_squared = [0, 0, 0]
        neigborColor = [0, 0, 0]
        color_neighborhood_average = [0, 0, 0]

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                coordinate_neighbor = ((list_available_coordinates[index][0] - 1 + i), (list_available_coordinates[index][1] - 1 + j))

                # neighbor must be in the canvas
                bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_painting.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_painting.shape[1]))
                if (bool_neighbor_in_canvas):

                    # neighbor must not be black
                    bool_neighbor_not_black = not numpy.array_equal(canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                    if (bool_neighbor_not_black):

                        # get colDiff between the neighbor and target colors, add it to the list
                        neigborColor = canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]]

                        color_neighborhood_average[0] += neigborColor[0]
                        color_neighborhood_average[1] += neigborColor[1]
                        color_neighborhood_average[2] += neigborColor[2]

                        # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                        color_difference[0] = int(color_selected[0]) - int(neigborColor[0])
                        color_difference[1] = int(color_selected[1]) - int(neigborColor[1])
                        color_difference[2] = int(color_selected[2]) - int(neigborColor[2])

                        color_difference_squared[0] = color_difference[0] * color_difference[0]
                        color_difference_squared[1] = color_difference[1] * color_difference[1]
                        color_difference_squared[2] = color_difference[2] * color_difference[2]

                        distance_euclidian_aproximation = color_difference_squared[0] + color_difference_squared[1] + color_difference_squared[2]

                        list_neighbor_diffs[index_neighbor_diffs] = distance_euclidian_aproximation
                        index_neighbor_diffs += 1

        # check operational mode and find the resulting distance
        if (mode_selected == 1):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):
                # return the minimum difference of all the neighbors
                distance_found = numpy.min(list_neighbor_diffs[0:index_neighbor_diffs])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        elif (mode_selected == 2):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):
                # return the minimum difference of all the neighbors
                distance_found = numpy.mean(list_neighbor_diffs[0:index_neighbor_diffs])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        elif (mode_selected == 3):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):

                color_neighborhood_average[0] = color_neighborhood_average[0]/index_neighbor_diffs
                color_neighborhood_average[1] = color_neighborhood_average[1]/index_neighbor_diffs
                color_neighborhood_average[2] = color_neighborhood_average[2]/index_neighbor_diffs

                # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                color_difference[0] = color_selected[0] - color_neighborhood_average[0]
                color_difference[1] = color_selected[1] - color_neighborhood_average[1]
                color_difference[2] = color_selected[2] - color_neighborhood_average[2]

                color_difference_squared[0] = color_difference[0] * color_difference[0]
                color_difference_squared[1] = color_difference[1] * color_difference[1]
                color_difference_squared[2] = color_difference[2] * color_difference[2]

                distance_found = color_difference_squared[0] + color_difference_squared[1] + color_difference_squared[2]

            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        # if it is the best so far save the value and its location
        if (distance_found < distance_minumum):
            distance_minumum = distance_found
            coordinate_minumum = list_available_coordinates[index]

    return (color_selected, coordinate_minumum)


# Enable Numba acceleration on getBestPositionForColor_bruteForce()
if config.PARSED_ARGS.j:
    getBestPositionForColor_bruteForce = numba.njit()(getBestPositionForColor_bruteForce)


# tracks a neighborhood around a coordinate in the two availabilty data structures
def trackNewBoundyNeighbors_bruteForce(coordinate_requested):

    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the location being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((coordinate_requested[0] - 1 + i), (coordinate_requested[1] - 1 + j))

            # neighbor must be in the canvas
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must also be black (not already colored)
                bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if (bool_neighbor_is_black):
                    trackCoordinate_bruteForce(coordinate_neighbor)


# tracks a coordinate in the two availabilty data structures
def trackCoordinate_bruteForce(coordinate_requested):

    # Global Access
    global count_available
    global list_availabilty
    global canvas_availability

    # Check the coordinate is not already being tracked
    if (not canvas_availability[coordinate_requested[0], coordinate_requested[1]]):
        list_availabilty.append(coordinate_requested)
        canvas_availability[coordinate_requested[0], coordinate_requested[1]] = True
        count_available += 1


# un-tracks a coordinate in the two availabilty data structures
def unTrackCoordinate_bruteForce(coordinate_requested):

    # Global Access
    global count_available
    global list_availabilty
    global canvas_availability

    # Check the coordinate is already being tracked
    if (canvas_availability[coordinate_requested[0], coordinate_requested[1]]):
        list_availabilty.remove((coordinate_requested[0], coordinate_requested[1]))
        canvas_availability[coordinate_requested[0], coordinate_requested[1]] = False
        count_available -= 1


# =============================================================================
# RTREE
# =============================================================================
def getBestPositionForColor_rTree(rgb_requested_color):
    return list(rTree_neighborhood_colors.nearest(getColorBoundingBox(rgb_requested_color), 1, objects='RAW'))


def trackNewBoundyNeighbors_rTree(coordinate_requested):
    # Get all 8 neighbors, Loop over the 3x3 grid surrounding the coordinate_requested being considered
    for i in range(3):
        for j in range(3):

            # this pixel is the coordinate_requested being considered;
            # it is not a neigbor, go to the next one
            if (i == 1 and j == 1):
                continue

            # calculate the neigbor's coordinates
            coordinate_neighbor = ((coordinate_requested[0] - 1 + i), (coordinate_requested[1] - 1 + j))

            # neighbor must be in the canvas
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_actual_color.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_actual_color.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must also not be black
                bool_neighbor_is_black = numpy.array_equal(canvas_actual_color[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if (bool_neighbor_is_black):
                    trackCoordinate_rTree(coordinate_neighbor)


# Track the given neighbor as available
#   if the location is already tracked, un-track it first, then re-track it.
#   this prevents duplicate availble locations, and updates the neighborhood color
# Tracking consists of:
#   inserting a new nearest_neighbor into the rTree_neighborhood_colors,
#   and flagging the associated location in the availabilityIndex
def trackCoordinate_rTree(coordinate_requested):

    # Globals
    global rTree_neighborhood_colors
    global canvas_id
    global canvas_availability
    global canvas_neighborhood_color
    global count_available
    global count_id

    # if the neighbor is already in the rTree_neighborhood_colors, then it needs to be deleted
    # otherwise there will be duplicate avialability with outdated neighborhood colors.
    if (canvas_availability[coordinate_requested[0], coordinate_requested[1]]):
        neighborID = canvas_id[coordinate_requested[0], coordinate_requested[1]]
        rgb_neighborhood_color = canvas_neighborhood_color[coordinate_requested[0], coordinate_requested[1]]
        rTree_neighborhood_colors.delete(neighborID, getColorBoundingBox(rgb_neighborhood_color))

        # flag the coordinate_requested as no longer being available
        canvas_availability[coordinate_requested[0], coordinate_requested[1]] = False
        count_available -= 1

    # get the newest neighborhood color
    rgb_neighborhood_color = getAverageColor(coordinate_requested)

    # update the coordinate_requested in the availability index
    canvas_availability[coordinate_requested[0]][coordinate_requested[1]] = True
    count_available += 1
    canvas_id[coordinate_requested[0]][coordinate_requested[1]] = count_id
    canvas_neighborhood_color[coordinate_requested[0]][coordinate_requested[1]] = rgb_neighborhood_color

    # add the coordinate_requested to the rTree_neighborhood_colors
    rTree_neighborhood_colors.insert(count_id, getColorBoundingBox(rgb_neighborhood_color), coordinate_requested)
    count_id += 1


# Un-Track the given nearest_neighbor
# Un-Tracking Consists of:
#   removing the given nearest_neighbor from the rTree_neighborhood_colors,
#   and Un-Flagging the associated location in the availabilityIndex
def unTrackCoordinate_rTree(nearest_neighbor):

    global count_available
    global count_id

    locationID = nearest_neighbor.id
    coordinate_nearest_neighbor = nearest_neighbor.object
    bbox_neighborhood_color = nearest_neighbor.bbox

    # remove object from the rTree_neighborhood_colors
    rTree_neighborhood_colors.delete(locationID, bbox_neighborhood_color)

    # flag the location as no longer being available
    canvas_availability[coordinate_nearest_neighbor[0], coordinate_nearest_neighbor[1]] = False
    count_available -= 1
    count_id -= 1


# =============================================================================
# PYTHON
# =============================================================================
if __name__ == '__main__':
    main()
