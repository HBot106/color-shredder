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

# painter settings
PRINT_RATE = config.painter['PRINT_RATE']
LOCATIONS_PER_PAINTER = config.painter['LOCATIONS_PER_PAINTER']
MIN_MULTI_WORKLOAD = config.painter['MIN_MULTI_WORKLOAD']
MAX_PAINTERS = os.cpu_count() * 2

# canvas settings
COLOR_BIT_DEPTH = config.canvas['COLOR_BIT_DEPTH']
CANVAS_SIZE = numpy.array([config.canvas['CANVAS_WIDTH'], config.canvas['CANVAS_HEIGHT']], numpy.uint32)
START_POINT = numpy.array([config.canvas['START_X'], config.canvas['START_Y']], numpy.uint32)

# special values
BLACK = numpy.array([0, 0, 0], numpy.uint32)
INVALID_COORD = numpy.array([-1, -1], numpy.int8)

# =============================================================================
# GLOBALS
# =============================================================================

# position in and the list of all colors to be placed
colors_taken_count = 0
total_number_of_colors = ((2**COLOR_BIT_DEPTH)**3)
all_colors_list = numpy.zeros([total_number_of_colors, 3], numpy.uint32)

# used for ongoing speed calculation
previous_print_time = time.time()

# tracked for informational printout / progress report
collision_count = 0
placed_colors_count = 0

# holds the current state of the canvas
# format: [x][y][R, G, B]
painting_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# New R-Tree data structure testing for lookup of available locations
spatial_index_properties = rTree.Property()
spatial_index_properties.storage = rTree.RT_Memory
spatial_index_properties.dimension = 3
spatial_index_properties.variant = rTree.RT_Star
spatial_index_properties.near_minimum_overlap_factor = 32
spatial_index_properties.leaf_capacity = 32
spatial_index_properties.index_capacity = 32
spatial_index_properties.fill_factor = 0.5
neighborhood_color_spatial_index = rTree.Index(properties=spatial_index_properties)

# holds neighborhood color for every location in the canvas in the following form:
# format [x][y][NC.R, NC.G, NC.B]
neighborhood_color_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# format[x][y]
availability_canvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1]], numpy.bool)
available_locations_count = 0

# format: [index][NC.R, NC.G, NC.B, x, y]
neighborhood_color_buffer = numpy.zeros([1000, 5], numpy.uint32)

# writes data arrays as PNG image files
png_writer = pypng.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

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
    while(available_locations_count and (colors_taken_count < total_number_of_colors)):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global colors_taken_count
    global painting_canvas
    global placed_colors_count

    # Setup
    starting_coordinate = numpy.array([START_POINT[0], START_POINT[1]], numpy.uint32)

    # get the starting color
    target_color = all_colors_list[colors_taken_count]
    colors_taken_count += 1

    # draw the first color at the starting location
    painting_canvas[starting_coordinate[0], starting_coordinate[1]] = target_color
    placed_colors_count += 1

    # add its neigbors to uncolored Boundary Region
    for neighbor in canvasTools.getNewBoundaryNeighbors(starting_coordinate, painting_canvas):

        trackNeighbor(neighbor)

    # finish first pixel
    printCurrentCanvas()


# continue the painting
def continuePainting():

    # Global Access
    global colors_taken_count

    # get the color to be placed
    target_color = all_colors_list[colors_taken_count]
    colors_taken_count += 1

    # find the best location for that color
    bestResult = getBestPositionForColor(target_color)
    resultCoord = bestResult[1]

    # attempt to paint the color at the corresponding location
    paintToCanvas(target_color, resultCoord)


def getBestPositionForColor(requestedColor):

    nearestSpatialColorIndexObjects = list(neighborhood_color_spatial_index.nearest(
        colorTools.getColorBoundingBox(requestedColor), 1, objects='RAW'))
    return [requestedColor, nearestSpatialColorIndexObjects]


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, nearestSpatialColorIndexObjects):

    # Global Access
    global collision_count
    global painting_canvas

    # retains ability to process k potential nearest neighbots even tho only one is requested
    for neighborhood_color_spatial_indexObject in nearestSpatialColorIndexObjects:
        # Setup
        requestedCoord = neighborhood_color_spatial_indexObject.object[0]

        # double check the the pixel is available
        if (canvasTools.isLocationBlack(requestedCoord, painting_canvas)):

            # the best position for requestedColor has been found color it
            painting_canvas[requestedCoord[0], requestedCoord[1]] = requestedColor

            unTrackNeighbor(neighborhood_color_spatial_indexObject)

            # each valid neighbor position should be added to uncolored Boundary Region
            for neighbor in canvasTools.getNewBoundaryNeighbors(requestedCoord, painting_canvas):

                trackNeighbor(neighbor)

            # print progress
            if (placed_colors_count % PRINT_RATE == 0):
                printCurrentCanvas()
            return

    # major collision
    collision_count += 1

def trackNeighbor(location):
    
    # Globals
    neighborhood_color = canvasTools.getAverageColor(location, painting_canvas)


    

def unTrackNeighbor(neighborhood_color_spatial_indexObject):
    global placed_colors_count



# prints the current state of painting_canvas as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global previous_print_time

    # get elapsed time
    currentTime = time.time()
    elapsed = currentTime - previous_print_time

    # exclude duplicate printings
    if (elapsed > 0):
        rate = PRINT_RATE/elapsed

        # cancel (probably a duplicate)
        if (rate > 500) and not (finalize):
            return

        # write the png file
        name = (FILENAME + '.png')
        myFile = open(name, 'wb')
        png_writer.write(myFile, canvasTools.toRawOutput(painting_canvas))
        myFile.close()

        # Info Print
        previous_print_time = currentTime
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            placed_colors_count, neighborhood_color_spatial_index.count([0, 0, 0, 256, 256, 256]), (placed_colors_count * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), collision_count, rate), end='\n')


def canvasSpatialIndexGenerator():
    global availability_canvas
    global available_locations_count

    for col in availability_canvas:
        for location in col:

            if (location[0]):

                neighborhoodColor = numpy.array([location[2], location[3], location[4]])

                yield (available_locations_count, colorTools.getColorBoundingBox(neighborhoodColor), [location, neighborhoodColor])
                available_locations_count += 1
# r = index.Index(generator_function())


if __name__ == '__main__':
    main()
