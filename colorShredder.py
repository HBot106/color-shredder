import png
import numpy

import sys
import concurrent.futures
import time

import colorTools
import config

# =============================================================================
# MACROS
# =============================================================================

COLOR_BLACK = numpy.array([0, 0, 0], numpy.uint32)
COORDINATE_INVALID = numpy.array([-1, -1])

# =============================================================================
# GLOBALS
# =============================================================================

# empty list of all colors to be placed and an index for tracking position in the list
list_all_colors = numpy.zeros([((2**config.canvas['COLOR_BIT_DEPTH'])**3), 3], numpy.uint32)
index_all_colors = 0

# empty list of all colors to be placed and an index for tracking position in the list
list_collided_colors = []
index_collided_colors = 0

# used for ongoing speed calculation
time_last_print = time.time()

# tracked for informational printout / progress report
count_collisions = 0
count_placed_colors = 0

# canvas and list for tracking available coordinates
canvas_availabilty = numpy.zeros([config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT']], numpy.bool)
list_availabilty = []
count_available = 0

# holds the current RGB state of the canvas
canvas_color_painting = numpy.zeros([config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT'], 3], numpy.uint32)

# writes data arrays as PNG image files
png_author = png.Writer(config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT'], greyscale=False)
# =============================================================================


def main():
    # Global Access
    global list_all_colors

    # Setup
    list_all_colors = colorTools.generateColors(config.canvas['COLOR_BIT_DEPTH'], config.color['MULTIPROCESSING'], config.color['SHUFFLE'])
    print("Painting Canvas...")
    time_started = time.time()

    # Work
    # # draw the first color at the starting pixel
    startPainting()

    # # while more un-colored boundry locations exist and there are more colors to be placed, continue painting
    while(count_available and (index_all_colors < list_all_colors.shape[0])):
        continuePainting()

    # # while more un-colored boundry locations exist and there are more collision colors to be placed, continue painting
    while(count_available and (index_collided_colors < len(list_collided_colors))):
        finishPainting()

    # Final Print Authoring
    time_elapsed = time.time() - time_started
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(time_elapsed / 60) + " minutes!")


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global index_all_colors

    # Setup
    color_selected = list_all_colors[index_all_colors]
    coordinate_start_point = numpy.array([config.canvas['START_X'], config.canvas['START_Y']])
    index_all_colors += 1

    # draw the first color at the starting pixel
    paintToCanvas(color_selected, coordinate_start_point)

    # for the 8 neighboring locations check that they are in the canvas and uncolored (black), then account for their availabity
    markValidNeighborsAvailable(coordinate_start_point)


# continue the painting
def continuePainting():

    # Global Access
    global index_all_colors

    # Setup
    # if more than MIN_MULTI_WORKLOAD locations are coordinate_available, allow multiprocessing
    if ((count_available > config.painter['MIN_MULTI_WORKLOAD']) and config.painter['MULTIPROCESSING']):
        mutliprocessing_painter_manager = concurrent.futures.ProcessPoolExecutor()
        list_painter_work_queue = []

        # cap the number of workers so that there are at least LOCATIONS_PER_PAINTER free locations per worker
        # this keeps the number of collisions down
        # loop over each one
        for _ in range(min(((count_available//config.painter['LOCATIONS_PER_PAINTER']), config.painter['MAX_PAINTERS']))):

            if (index_all_colors < len(list_all_colors)):
                # get the color to be placed
                color_selected = list_all_colors[index_all_colors]
                index_all_colors += 1

                # schedule a worker to find the best location for that color
                list_neighbor_diffs = numpy.zeros(8, numpy.uint32)
                list_painter_work_queue.append(mutliprocessing_painter_manager.submit(getBestPositionForColor, color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_color_painting))

        # as each worker completes
        for painter_worker in concurrent.futures.as_completed(list_painter_work_queue):

            # collect the best location for that color
            worker_color_selected = painter_worker.result()[0]
            worker_corrdinate_selected = painter_worker.result()[1]

            # attempt to paint the color at the corresponding location
            paintToCanvas(worker_color_selected, worker_corrdinate_selected)

        # teardown the process pool
        mutliprocessing_painter_manager.shutdown()

    # otherwise, use only the main process
    # This is because the overhead of multithreading makes singlethreading better for small problems
    else:
        # get the color to be placed
        color_selected = list_all_colors[index_all_colors]
        index_all_colors += 1

        # find the best location for that color
        list_neighbor_diffs = numpy.zeros(8, numpy.uint32)
        coordinate_selected = getBestPositionForColor(color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_color_painting)[1]

        # attempt to paint the color at the corresponding location
        paintToCanvas(color_selected, coordinate_selected)

# finish the painting by using the same strategy but on the list of all colors that were not placed due to collisions


def finishPainting():
    global index_collided_colors

    # get the color to be placed
    color_selected = list_collided_colors[index_collided_colors]
    index_collided_colors += 1

    # find the best location for that color
    list_neighbor_diffs = numpy.zeros(8, numpy.uint32)
    coordinate_selected = getBestPositionForColor(color_selected, list_neighbor_diffs, numpy.array(list_availabilty), canvas_color_painting)[1]

    # attempt to paint the color at the corresponding location
    paintToCanvas(color_selected, coordinate_selected)


# Gives the best location among all avilable for the requested color; Also returns the color itself
# # In other words, checks every coordinate_available location using considerPixelAt(), keeping track of the
# # minimum (best/closest) value returned and the location associated with it, this location "coordinate_minumum"
# # is where we will place the target color
# @njit
def getBestPositionForColor(color_selected, list_neighbor_diffs, list_available_coordinates, canvas_painting):

    # reset minimums
    coordinate_minumum = COORDINATE_INVALID
    distance_minumum = sys.maxsize

    # for every coordinate_available position in the boundry, perform the check, keep the best position:
    for coordinate_available in list_available_coordinates:

        index_neighbor_diffs = 0
        list_neighbor_diffs.fill(0)
        color_neighborhood_average = canvas_painting[coordinate_available[0], coordinate_available[1]]

        # Get all 8 neighbors, Loop over the 3x3 grid surrounding the location being considered
        for i in range(3):
            for j in range(3):

                # this pixel is the location being considered;
                # it is not a neigbor, go to the next one
                if (i == 1 and j == 1):
                    continue

                # calculate the neigbor's coordinates
                coordinate_neighbor = ((coordinate_available[0] - 1 + i), (coordinate_available[1] - 1 + j))

                # neighbor must be in the canvas
                bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_painting.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_painting.shape[1]))
                if (bool_neighbor_in_canvas):

                    # neighbor must not be black (don't include uncolored neighbors)
                    bool_neighbor_not_black = not numpy.array_equal(canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                    if (bool_neighbor_not_black):

                        # get colDiff between the neighbor and target colors, add it to the list
                        neigborColor = canvas_painting[coordinate_neighbor[0], coordinate_neighbor[1]]
                        color_neighborhood_average = numpy.add(color_neighborhood_average, neigborColor)

                        # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                        color_difference = numpy.subtract(color_selected, neigborColor)
                        color_difference_squared = numpy.multiply(color_difference, color_difference)
                        distance_euclidian_aproximation = numpy.sum(color_difference_squared)

                        list_neighbor_diffs[index_neighbor_diffs] = distance_euclidian_aproximation
                        index_neighbor_diffs += 1

        # check operational mode and find the resulting distance
        if (config.mode['CURRENT'] == 0):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):
                # return the minimum difference of all the neighbors
                distance_found = numpy.min(list_neighbor_diffs[0:index_neighbor_diffs])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        elif (config.mode['CURRENT'] == 1):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):
                # return the minimum difference of all the neighbors
                distance_found = numpy.mean(list_neighbor_diffs[0:index_neighbor_diffs])
            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        elif (config.mode['CURRENT'] == 2):
            # check if the considered pixel has at least one valid neighbor
            if (index_neighbor_diffs):

                index_array = numpy.array([index_neighbor_diffs, index_neighbor_diffs, index_neighbor_diffs])
                color_neighborhood_average = numpy.divide(color_neighborhood_average, index_array)

                # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
                color_difference = numpy.subtract(color_selected, color_neighborhood_average)
                color_difference_squared = numpy.multiply(color_difference, color_difference)
                distance_found = numpy.sum(color_difference_squared)
            # if it has no valid neighbors, maximise its colorDiff
            else:
                distance_found = sys.maxsize

        # if it is the best so far save the value and its location
        if (distance_found < distance_minumum):
            distance_minumum = distance_found
            coordinate_minumum = coordinate_available

    return (color_selected, coordinate_minumum)


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requestedCoord):

    # Global Access
    global count_collisions
    global count_placed_colors
    global canvas_color_painting

    # double check the the pixel is COLOR_BLACK
    bool_coordinate_is_black = numpy.array_equal(canvas_color_painting[requestedCoord[0], requestedCoord[1]], COLOR_BLACK)
    if (bool_coordinate_is_black):

        # the best position for requestedColor has been found color it, and mark it unavailable
        canvas_color_painting[requestedCoord[0], requestedCoord[1]] = requestedColor
        markCoordinateUnavailable(requestedCoord)
        count_placed_colors += 1

        # for the 8 neighboring locations check that they are in the canvas and uncolored (black), then account for their availabity
        markValidNeighborsAvailable(requestedCoord)

    # collision
    else:
        list_collided_colors.append(requestedColor)
        count_collisions += 1

    # print progress
    if (count_placed_colors % config.painter['PRINT_RATE'] == 0):
        printCurrentCanvas()


def markValidNeighborsAvailable(coordinate_requested):

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
            bool_neighbor_in_canvas = ((0 <= coordinate_neighbor[0] < canvas_color_painting.shape[0]) and (0 <= coordinate_neighbor[1] < canvas_color_painting.shape[1]))
            if (bool_neighbor_in_canvas):

                # neighbor must also be black (not already colored)
                bool_neighbor_is_black = numpy.array_equal(canvas_color_painting[coordinate_neighbor[0], coordinate_neighbor[1]], COLOR_BLACK)
                if (bool_neighbor_is_black):
                    markCoordinateAvailable(coordinate_neighbor)


# tracks a coordinate in the two availabilty data structures
def markCoordinateAvailable(coordinate_requested):

    # Global Access
    global count_available
    global list_availabilty
    global canvas_availabilty

    # Check the coordinate is not already being tracked
    if (not canvas_availabilty[coordinate_requested[0], coordinate_requested[1]]):
        list_availabilty.append(coordinate_requested)
        canvas_availabilty[coordinate_requested[0], coordinate_requested[1]] = True
        count_available += 1


# un-tracks a coordinate in the two availabilty data structures
def markCoordinateUnavailable(coordinate_requested):

    # Global Access
    global count_available
    global list_availabilty
    global canvas_availabilty

    # Check the coordinate is already being tracked
    if (canvas_availabilty[coordinate_requested[0], coordinate_requested[1]]):
        list_availabilty.remove((coordinate_requested[0], coordinate_requested[1]))
        canvas_availabilty[coordinate_requested[0], coordinate_requested[1]] = False
        count_available -= 1


# converts a canvas into raw data for writing to a png
def toRawOutput(canvas):

    # converts the given canvas into a format that the PNG module can use to write a png
    canvas_8bit = numpy.array(canvas, numpy.uint8)
    canvas_transposed = numpy.transpose(canvas_8bit, (1, 0, 2))
    canvas_flipped = numpy.flip(canvas_transposed, 2)
    return numpy.reshape(canvas_flipped, (canvas.shape[1], canvas.shape[0] * 3))


# prints the current state of canvas_color_painting as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global time_last_print
    global png_author

    # get time_elapsed time
    time_current = time.time()
    time_elapsed = time_current - time_last_print

    # exclude duplicate printings
    if (time_elapsed > 0):
        painting_rate = config.painter['PRINT_RATE']/time_elapsed

        # cancel (probably a duplicate)
        if (painting_rate > 500) and not (finalize):
            return

        # write the png file
        painting_output_name = (config.painter["PAINTING_NAME"] + '.png')
        painting_output_file = open(painting_output_name, 'wb')
        png_author.write(painting_output_file, toRawOutput(canvas_color_painting))
        painting_output_file.close()

        # Info Print
        time_last_print = time_current
        info_print = "Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec."
        print(info_print.format(count_placed_colors, count_available, (count_placed_colors * 100 / config.canvas['CANVAS_WIDTH'] / config.canvas['CANVAS_HEIGHT']), count_collisions, painting_rate), end='\n')

    if (config.painter['DEBUG_WAIT']):
        time.sleep(config.painter['DEBUG_WAIT_TIME'])


if __name__ == '__main__':
    main()
