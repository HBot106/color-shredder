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
# name of the output PNG file
FILENAME = config.output['FILENAME']

# color selection mode
MODE = config.mode['DEFAULT']

# color generation settings
SHUFFLE_COLORS = config.color['SHUFFLE']
USE_MULTIPROCESSING = config.color['MULTIPROCESSING']
COLOR_BIT_DEPTH = config.canvas['COLOR_BIT_DEPTH']
NUMBER_OF_COLORS = ((2**COLOR_BIT_DEPTH)**3)

# painter settings
PRINT_RATE = config.painter['PRINT_RATE']
LOCATIONS_PER_PAINTER = config.painter['LOCATIONS_PER_PAINTER']
MIN_MULTI_WORKLOAD = config.painter['MIN_MULTI_WORKLOAD']
MAX_PAINTERS = os.cpu_count() * 2

# canvas settings
CANVAS_SIZE = numpy.array([config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT']], numpy.uint32)
START_POINT = numpy.array([config.canvas['START_X'], config.canvas['START_Y']], numpy.uint32)

# special values
BLACK = numpy.array([0, 0, 0], numpy.uint32)
INVALID_COORD = numpy.array([-1, -1], numpy.int8)
INVALID_DISTANCE = sys.maxsize

MAX_BUFFER_SIZE = 1000
K_NEIGHBORS = 10

# =============================================================================
# GLOBALS
# =============================================================================

# position in and the list of all colors to be placed
all_colors_list = numpy.zeros([NUMBER_OF_COLORS, 3], numpy.uint32)

# used for ongoing speed calculation
previous_print_time = time.time()

# holds the current state of the output painting
# format: [x][y][R, G, B] uint32
painting_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# holds neighborhood color for every location in the canvas in the following form:
# format [x][y][NC.R, NC.G, NC.B] uint32
neighborhood_color_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# holds state of availability for every location on the canvas
# format[x][y] bool
availability_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.bool)

# rTree for quick neighborhood color nearest neighbor searches
spatial_index_properties = rTree.Property()
spatial_index_properties.storage = rTree.RT_Memory
spatial_index_properties.dimension = 3
spatial_index_properties.variant = rTree.RT_Star
spatial_index_properties.near_minimum_overlap_factor = 32
spatial_index_properties.leaf_capacity = 32
spatial_index_properties.index_capacity = 32
spatial_index_properties.fill_factor = 0.5
neighborhood_color_spatial_index = rTree.Index(properties=spatial_index_properties)

# format: [index][NC.R, NC.G, NC.B, x, y]
neighborhood_color_buffer = numpy.zeros([MAX_BUFFER_SIZE, 5], numpy.uint32)

# writes data arrays as PNG image files
png_writer = pypng.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

# various counters
count_colors_taken = 0
count_collisions = 0
count_placed_colors = 0
count_available_locations = 0
count_buffered_records = 0

# =============================================================================


def main():
    # Global Access
    global all_colors_list

    # Setup
    all_colors_list = colorTools.generateColors(COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    start_time = time.time()
    paintCanvas()
    elapsed_time = time.time() - start_time

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(elapsed_time / 60) + " minutes!")


# manages painting of the canvas
def paintCanvas():

    # draw the first color at the starting pixel
    startPainting()

    # while 2 conditions, continue painting:
    #   1) more un-colored boundry locations exist
    #   2) there are more generated colors to be placed
    while(count_available_locations and (count_colors_taken < NUMBER_OF_COLORS)):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global count_colors_taken
    global painting_canvas
    global count_placed_colors

    # Setup
    starting_coordinate = numpy.array([START_POINT[0], START_POINT[1]], numpy.uint32)

    # get the starting color
    target_color = all_colors_list[count_colors_taken]
    count_colors_taken += 1

    # draw the first color at the starting location
    painting_canvas[starting_coordinate[0], starting_coordinate[1]] = target_color
    count_placed_colors += 1

    # add its neigbors to uncolored Boundary Region
    for neighbor in canvasTools.getNewBoundaryNeighbors(starting_coordinate, painting_canvas):

        trackNeighbor(neighbor)

    # finish first pixel
    printCurrentCanvas()


# continue the painting
def continuePainting():

    # Global Access
    global count_colors_taken

    # get the color to be placed
    target_color = all_colors_list[count_colors_taken]
    count_colors_taken += 1

    # find the best location for that color
    result_coordinate = getBestPositionForColor(target_color)

    if (numpy.array_equal(result_coordinate, INVALID_COORD)):
        neighborhood_color_spatial_index = rTree.Index(canvasSpatialIndexGenerator(), properties=spatial_index_properties)

    # attempt to paint the color at the corresponding location
    paintToCanvas(target_color, result_coordinate)


def getBestPositionForColor(requestedColor):

    # setup
    best_position = INVALID_COORD
    best_color = BLACK
    best_distance = INVALID_DISTANCE

    # if the spatial index has colors
    if (neighborhood_color_spatial_index.count([0, 0, 0, 256, 256, 256])):
        
        # get the k nearest neighbors to the requested color
        k_nearest_neighbors_list = list(neighborhood_color_spatial_index.nearest(colorTools.getColorBoundingBox(requestedColor), K_NEIGHBORS, objects='RAW'))
    
        # check up to k nearest neighbors from the spatial index
        for nearest_neighbor in k_nearest_neighbors_list:

            # breakdown the spatial index record
            nearest_neighbor_coordinate = nearest_neighbor.object
            nearest_neighbor_neighborhood_color = nearest_neighbor.bbox[0:3]
            nearest_neighbor_unused_id = nearest_neighbor.id
            
            # if the location is actually still available:
            if (availability_canvas[nearest_neighbor_coordinate[0], nearest_neighbor_coordinate[1]]):
                
                # the best position from the spatial index has been found
                best_position = nearest_neighbor_coordinate
                best_color = nearest_neighbor_neighborhood_color
                best_distance = colorTools.getColorDiff(requestedColor, best_color)

                # now every position in the buffer is checked for an even better result
                for index in range(count_buffered_records):
                    
                    # get the distance
                    buffer_record_color = neighborhood_color_buffer[index][0:3]
                    buffer_record_coordinate = neighborhood_color_buffer[index][3:5]
                    buffer_record_distance = colorTools.getColorDiff(requestedColor, buffer_record_color)

                    # is the buffer record better and is its location still available?
                    if ((buffer_record_distance < best_distance) and (availability_canvas[buffer_record_coordinate])):
                        
                        # even better position found
                        best_distance = buffer_record_distance
                        best_color = buffer_record_color
                        best_position = buffer_record_coordinate

                # a "best" position was found, no need to check the remaining k neighbors
                break
        
        # best_position will be INVALID_POSITION if none of the k nearest neighbors is actually available
        # when this happens the spatial index should be rebuilt and the best position querry should be repeated
        return best_position

    else:
        # the spatial index is empty, just check the buffer
        for index in range(count_buffered_records):
            
            # get the distance
            buffer_record_color = neighborhood_color_buffer[index][0:3]
            buffer_record_coordinate = neighborhood_color_buffer[index][3:5]
            buffer_record_distance = colorTools.getColorDiff(requestedColor, buffer_record_color)

            # is the buffer record better and is its location still available?
            if ((buffer_record_distance < best_distance) and (availability_canvas[buffer_record_coordinate[0], buffer_record_coordinate[1]])):
                
                # even better position found
                best_distance = buffer_record_distance
                best_color = buffer_record_color
                best_position = buffer_record_coordinate

        return best_position


    


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, requested_coordinate):

    # Global Access
    global count_collisions
    global painting_canvas

    # double check the the pixel is available
    if (canvasTools.isLocationBlack(requested_coordinate, painting_canvas)):

        # the best position for requestedColor has been found color it
        painting_canvas[requested_coordinate[0], requested_coordinate[1]] = requestedColor

        unTrackNeighbor(requested_coordinate)

        # each valid neighbor position should be added to uncolored Boundary Region
        for neighbor in canvasTools.getNewBoundaryNeighbors(requested_coordinate, painting_canvas):

            trackNeighbor(neighbor)

        # print progress
        if (count_placed_colors % PRINT_RATE == 0):
            printCurrentCanvas()
    
    else:            
        # major collision
        count_collisions += 1


def trackNeighbor(location):

    # Globals
    global availability_canvas
    global neighborhood_color_canvas
    global neighborhood_color_buffer
    global neighborhood_color_spatial_index

    global count_available_locations
    global count_buffered_records


    # mark location as available
    availability_canvas[location] = True
    count_available_locations += 1

    # get neighborhood color
    neighborhood_color = canvasTools.getAverageColor(location, painting_canvas)

    # record neighborhood color
    neighborhood_color_canvas[location] = neighborhood_color

    # if there is room in the buffer, make an entry there
    if (count_buffered_records < MAX_BUFFER_SIZE):
        neighborhood_color_buffer[count_buffered_records] = numpy.append(neighborhood_color, location)
        count_buffered_records += 1
    # otherwise, rebuild the rTree
    else:
        # rebuild spatial index
        neighborhood_color_spatial_index = rTree.Index(canvasSpatialIndexGenerator(), properties=spatial_index_properties)


def unTrackNeighbor(location):
    # globals
    global availability_canvas
    global count_available_locations

    availability_canvas[location] = False
    count_available_locations -= 1
    

# prints the current state of painting_canvas as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global previous_print_time

    # get elapsed_time time
    current_time = time.time()
    elapsed_time = current_time - previous_print_time

    # exclude duplicate printings
    if (elapsed_time > 0):
        rate = PRINT_RATE/elapsed_time

        # cancel (probably a duplicate)
        if (rate > 500) and not (finalize):
            return

        # write the png file
        name = (FILENAME + '.png')
        output_file = open(name, 'wb')
        png_writer.write(output_file, canvasTools.toRawOutput(painting_canvas))
        output_file.close()

        # Info Print
        previous_print_time = current_time
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(count_placed_colors, count_available_locations, (count_placed_colors * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), count_collisions, rate), end='\n')


def canvasSpatialIndexGenerator():
    global neighborhood_color_buffer

    # clear the buffer, the data is non essential and about to get built into the spatial index
    neighborhood_color_buffer = numpy.zeros([MAX_BUFFER_SIZE, 5], numpy.uint32)

    # loop over the whole canvas
    for x in range(CANVAS_SIZE[0]):
        for y in range(CANVAS_SIZE[1]):

            # if it is available its neighborhood color should be added to the spatial index
            if (availability_canvas[x, y]):
                count_available_locations += 1
                neighborhoodColor = neighborhood_color_canvas[x, y]
                yield (0, colorTools.getColorBoundingBox(neighborhoodColor), numpy.array([x, y], numpy.uint32))
                
# r = index.Index(generator_function())


if __name__ == '__main__':
    main()
