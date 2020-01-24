import png as pypng
import numpy
from rtree import index as rTree

import os
import sys
import concurrent.futures
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
colorCount = 0
TOTAL_NUMBER_OF_COLORS = ((2**COLOR_BIT_DEPTH)**3)
allColors = numpy.zeros([TOTAL_NUMBER_OF_COLORS, 3], numpy.uint32)

# used for ongoing speed calculation
lastPrintTime = time.time()

# tracked for informational printout / progress report
collisionCount = 0
coloredCount = 0

# New R-Tree data structure testing for lookup of available locations
indexProperties = rTree.Property()
indexProperties.storage = rTree.RT_Memory
indexProperties.dimension = 3
indexProperties.variant = rTree.RT_Star
spatialColorIndex = rTree.Index(properties=indexProperties)

# holds the current state of the canvas
workingCanvas = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 3], numpy.uint32)

# holds availability information for every location in the canvas in the following form:
# [x][y][isInSpatialColorIndexBoolean, #ID, neighborhoodColor.R, neighborhoodColor.G, neighborhoodColor.B]
availabilityIndex = numpy.zeros([CANVAS_SIZE[0], CANVAS_SIZE[1], 5], numpy.uint32)
locationsMadeAvailCount = 0

# writes data arrays as PNG image files
pngWriter = pypng.Writer(CANVAS_SIZE[0], CANVAS_SIZE[1], greyscale=False)

# =============================================================================


def main():
    # Global Access
    global allColors

    # Setup
    allColors = colorTools.generateColors(COLOR_BIT_DEPTH, USE_MULTIPROCESSING, SHUFFLE_COLORS)

    # Work
    print("Painting Canvas...")
    beginTime = time.time()
    paintCanvas()
    elapsedTime = time.time() - beginTime

    # Final Print Authoring
    printCurrentCanvas(True)
    print("Painting Completed in " + "{:3.2f}".format(elapsedTime / 60) + " minutes!")


# manages painting of the canvas
def paintCanvas():

    # draw the first color at the starting pixel
    startPainting()

    # while 2 conditions, continue painting:
    #   1) more un-colored boundry locations exist
    #   2) there are more generated colors to be placed
    while(spatialColorIndex.count([0, 0, 0, 256, 256, 256]) and (colorCount < TOTAL_NUMBER_OF_COLORS)):
        continuePainting()


# start the painting, by placing the first target color
def startPainting():

    # Global Access
    global colorCount
    global spatialColorIndex
    global availabilityIndex
    global locationsMadeAvailCount
    global workingCanvas
    global coloredCount

    # Setup
    startPoint = numpy.array([START_POINT[0], START_POINT[1]], numpy.uint32)
    targetColor = allColors[colorCount]

    # draw the first color at the starting pixel
    workingCanvas[startPoint[0], startPoint[1]] = targetColor
    colorCount += 1

    # add its neigbors to uncolored Boundary Region
    for neighbor in canvasTools.getNewBoundaryNeighbors(startPoint, workingCanvas):
        
        neighborhoodColor = canvasTools.getAverageColor(neighbor, workingCanvas)

        # add the neighbor to the availability index
        locationAvailability = numpy.array(
            [1, locationsMadeAvailCount, neighborhoodColor[0], neighborhoodColor[1], neighborhoodColor[2]], numpy.uint32)
        availabilityIndex[neighbor[0]][neighbor[1]] = locationAvailability
        # print("Flagged location: " + str(neighbor) + " with: " + str(locationAvailability))
        
        # add the neighbor to the spatialColorIndex
        # insert(id(unused_flag), boundingBox(color), object(location, neighborhoodColor))
        spatialColorIndex.insert(
            locationsMadeAvailCount, colorTools.getColorBoundingBox(neighborhoodColor), [neighbor, neighborhoodColor])
        locationsMadeAvailCount += 1
        # print("Added color: " + str(neighborhoodColor) + " with ID: " + str(locationsMadeAvailCount) + " and location: " + str(neighbor))
        # print()

    # finish first pixel
    coloredCount = 1
    printCurrentCanvas()


# continue the painting
def continuePainting():

    # Global Access
    global colorCount
    global spatialColorIndex
    global workingCanvas
    global coloredCount

    # Setup
    availableCount = spatialColorIndex.count([0, 0, 0, 256, 256, 256])

    # if more than MIN_MULTI_WORKLOAD locations are available, allow multiprocessing
    if ((availableCount > MIN_MULTI_WORKLOAD) and USE_MULTIPROCESSING):
        painterManager = concurrent.futures.ProcessPoolExecutor()
        painters = []

        # cap the number of workers so that there are at least LOCATIONS_PER_PAINTER free locations per worker
        # this keeps the number of collisions down
        # loop over each one
        for _ in range(min(((availableCount//LOCATIONS_PER_PAINTER), MAX_PAINTERS))):

            if(len(allColors) > colorCount):
                # get the color to be placed
                targetColor = allColors[colorCount]
                colorCount += 1

                # schedule a worker to find the best location for that color
                painters.append(painterManager.submit(getBestPositionForColor, targetColor))

        # as each worker completes
        for painter in concurrent.futures.as_completed(painters):

            # collect the best location for that color
            workerResult = painter.result()
            workerTargetColor = workerResult[0]
            workerMinCoord = workerResult[1]

            # attempt to paint the color at the corresponding location
            paintToCanvas(workerTargetColor, workerMinCoord)

        # teardown the process pool
        painterManager.shutdown()

    # otherwise, use only the main process
    # This is because the overhead of multithreading makes singlethreading better for small problems
    else:
        # get the color to be placed
        targetColor = allColors[colorCount]
        colorCount += 1

        # find the best location for that color
        bestResult = getBestPositionForColor(targetColor)
        resultColor = bestResult[0]
        resultCoord = bestResult[1]

        # attempt to paint the color at the corresponding location
        paintToCanvas(targetColor, resultCoord)


# Gives the best location among all avilable for the requested color; Also returns the color itself
# # In other words, checks every available location using considerPixelAt(), keeping track of the
# # minimum (best/closest) value returned and the location associated with it, this location "MinCoord"
# # is where we will place the target color
def getBestPositionForColor(requestedColor):

    nearestSpatialColorIndexObjects = list(spatialColorIndex.nearest(
        colorTools.getColorBoundingBox(requestedColor), 1, True))
    return [requestedColor, nearestSpatialColorIndexObjects]


# attempts to paint the requested color at the requested location; checks for collisions
def paintToCanvas(requestedColor, nearestSpatialColorIndexObjects):

    # Global Access
    global collisionCount
    global coloredCount
    global spatialColorIndex
    global availabilityIndex
    global locationsMadeAvailCount
    global workingCanvas

    for spatialColorIndexObject in nearestSpatialColorIndexObjects:
        # Setup
        locationID = spatialColorIndexObject.id
        requestedCoord = spatialColorIndexObject.object[0]
        neighborhoodColor = spatialColorIndexObject.object[1]
        neighborhoodColorBBox = spatialColorIndexObject.bbox

        # double check the the pixel is available
        if (canvasTools.isLocationBlack(requestedCoord, workingCanvas)):

            # the best position for requestedColor has been found color it
            workingCanvas[requestedCoord[0], requestedCoord[1]] = requestedColor

            # remove object from the spatialColorIndex
            spatialColorIndex.delete(locationID, neighborhoodColorBBox)
            coloredCount += 1
            # print("Deleted color: " + str(neighborhoodColor) + " with ID: " + str(locationID) + " and location: " + str(requestedCoord))

            # flag the location as no longer being available
            availabilityIndex[requestedCoord[0], requestedCoord[1], 0] = 0
            # print("Un-Flagged location: " + str(requestedCoord))
            # print()

            # each valid neighbor position should be added to uncolored Boundary Region
            for neighbor in canvasTools.getNewBoundaryNeighbors(requestedCoord, workingCanvas):

                # if the neighbor is already in the spatialColorIndex, then it needs to be deleted
                # otherwise there will be duplicate avialability with outdated neighborhood colors.
                if (availabilityIndex[neighbor[0], neighbor[1], 0]):
                    # print("removing duplicate")
                    neighborID = availabilityIndex[neighbor[0], neighbor[1], 1]
                    neighborNeighborhoodColor = availabilityIndex[neighbor[0], neighbor[1], 2:5]
                    spatialColorIndex.delete(neighborID, colorTools.getColorBoundingBox(neighborNeighborhoodColor))
                    # print("Deleted color: " + str(neighborNeighborhoodColor) + " with ID: " + str(neighborID) + " and location: " + str(neighbor))

                    availabilityIndex[neighbor[0], neighbor[1], 0] = 0
                    # print("Un-Flagged location: " + str(neighbor))
                    # print()


                # get the newest avgColor
                neighborhoodColor = canvasTools.getAverageColor(neighbor, workingCanvas)

                # update the neighbor in the availability index
                locationAvailability = numpy.array(
                    [1, locationsMadeAvailCount, neighborhoodColor[0], neighborhoodColor[1], neighborhoodColor[2]], numpy.uint32)
                availabilityIndex[neighbor[0]][neighbor[1]] = locationAvailability
                # print("Flagged location: " + str(neighbor) + " with: " + str(locationAvailability))
                
                # add the neighbor to the spatialColorIndex
                # insert(id(unused_flag), boundingBox(color), object(location, neighborhoodColor))
                spatialColorIndex.insert(
                    locationsMadeAvailCount, colorTools.getColorBoundingBox(neighborhoodColor), [neighbor, neighborhoodColor])
                locationsMadeAvailCount += 1
                # print("Added color: " + str(neighborhoodColor) + " with ID: " + str(locationsMadeAvailCount) + " and location: " + str(neighbor))
                # print()

            # print progress
            if (coloredCount % PRINT_RATE == 0):
                printCurrentCanvas()
            return

    # major collision
    collisionCount += 1


# prints the current state of workingCanvas as well as progress stats
def printCurrentCanvas(finalize=False):

    # Global Access
    global lastPrintTime

    # get elapsed time
    currentTime = time.time()
    elapsed = currentTime - lastPrintTime

    # exclude duplicate printings
    if (elapsed > 0):
        rate = PRINT_RATE/elapsed

        # cancel (probably a duplicate)
        if (rate > 500) and not (finalize):
            return

        # write the png file
        name = (FILENAME + '.png')
        myFile = open(name, 'wb')
        pngWriter.write(myFile, canvasTools.toRawOutput(workingCanvas))
        myFile.close()

        # Info Print
        lastPrintTime = currentTime
        print("Pixels Colored: {}. Pixels Available: {}. Percent Complete: {:3.2f}. Total Collisions: {}. Rate: {:3.2f} pixels/sec.".format(
            coloredCount, spatialColorIndex.count([0, 0, 0, 256, 256, 256]), (coloredCount * 100 / CANVAS_SIZE[0] / CANVAS_SIZE[1]), collisionCount, rate), end='\n')
        # print("######################################################################")
        # print()
        # print()
        # time.sleep(1.0)


if __name__ == '__main__':
    main()
