import concurrent.futures
import time
import numpy

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# get the squared difference to another color
def getColorDiff(targetColor_A, targetColor_B):

    # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
    colorDifference = numpy.subtract(targetColor_A, targetColor_B)
    differenceSquared = numpy.multiply(colorDifference, colorDifference)
    squaresSum = numpy.sum(differenceSquared)

    # to get distance the sqrt must be taken, but we don't care about the actual distance, just relative distances, so we skip the sqrt for a constant runtime improvement
    # return numpy.sqrt(squaresSum)
    return squaresSum


# generate all colors of the color space, then shuffle the resulting array
def generateColors(COLOR_BIT_DEPTH, useMulti, useShuffle):

    # Setup, how many colors are needed?
    valuesPerChannel = 2**COLOR_BIT_DEPTH
    totalColors = valuesPerChannel**3
    allColors = numpy.zeros([totalColors, 3], numpy.uint32)

    # Info Print
    beginTime = time.time()
    print("Generating colors... {:3.2f}".format(
        0) + '%' + " complete.", end='\r')

    # choose single or multi processing
    if (useMulti):
        allColors = generateColorsMulti(COLOR_BIT_DEPTH, valuesPerChannel, totalColors)
    else:
        allColors = generateColorsSingle(COLOR_BIT_DEPTH, valuesPerChannel, totalColors)

    # Info Print
    elapsedTime = time.time() - beginTime
    print("Generating colors... {:3.2f}".format(100) + '%' + " complete.", end='\n')
    print("Generated {} colors in {:3.2f} seconds.".format(totalColors, elapsedTime))

    # Suffle the color list, so it is in a random order
    if (useShuffle):
        beginTime = time.time()
        print("Shuffling colors...", end='\r')
        numpy.random.shuffle(allColors)
        elapsedTime = time.time() - beginTime
        print("Shuffled {} colors in {:3.2f} seconds.".format(totalColors, elapsedTime))

    return allColors


# generate all colors of the color space, don't use multiprocessing
def generateColorsSingle(COLOR_BIT_DEPTH, valuesPerChannel, totalColors):

    # Setup
    workingColor = numpy.zeros([1, 3], numpy.uint32)
    allColors = numpy.zeros([totalColors, 3], numpy.uint32)
    index = 0

    # Generate all colors by looping over all r,g,b values
    for r in range(valuesPerChannel):
        for g in range(valuesPerChannel):
            for b in range(valuesPerChannel):
                # insert the color in its place
                workingColor = numpy.array([
                    int((r / valuesPerChannel) * 255),
                    int((g / valuesPerChannel) * 255),
                    int((b / valuesPerChannel) * 255)], numpy.uint32)
                allColors[index] = workingColor
                index += 1

        # Info Print
        print("Generating colors... {:3.2f}".format(100*r/valuesPerChannel) + '%' + " complete.", end='\r')

    # generation completed
    return allColors


# generate all colors of the color space, use multiprocessing
def generateColorsMulti(COLOR_BIT_DEPTH, valuesPerChannel, totalColors):

    # Setup
    allColors = numpy.zeros([totalColors, 3], numpy.uint32)

    # using multiprocessing kick off a worker for each red value in range of red values
    generator = concurrent.futures.ProcessPoolExecutor()
    constantReds = [generator.submit(generateColors_worker, red, valuesPerChannel) for red in range(valuesPerChannel)]

    # for each worker as it completes, insert its results into the array
    # the order that this happens does not matter as the array will be shuffled anywasys
    index = 0
    for constantRed in concurrent.futures.as_completed(constantReds):
        allColors[index * (valuesPerChannel**2): (index + 1) * (valuesPerChannel**2)] = constantRed.result()
        index += 1
        print("Generating colors... {:3.2f}".format(100*index/valuesPerChannel) + '%' + " complete.", end='\r')

    # generation completed
    return allColors


# for a given red value generate every color possible with the remaing green and blue values
def generateColors_worker(r, valuesPerChannel):

    # Setup
    workerColors = numpy.zeros([valuesPerChannel**2, 3], numpy.uint32)
    workingColor = numpy.zeros([1, 3], numpy.uint32)
    index = 0

    # loop over every value of green and blue producing each color that can have the given red value
    for g in range(valuesPerChannel):
        for b in range(valuesPerChannel):
            # insert the color in its place
            workingColor = numpy.array([
                int((r / valuesPerChannel) * 255),
                int((g / valuesPerChannel) * 255),
                int((b / valuesPerChannel) * 255)], numpy.uint32)
            workerColors[index] = workingColor
            index += 1

    # return all colors with the given red value
    return workerColors

# turn a given color into its bounding box representation
# numpy[r,g,b] -> (r,r,g,g,b,b)


def getColorBoundingBox(givenColor):
    if (givenColor.size == 3):
        return (givenColor[0], givenColor[1], givenColor[2], givenColor[0], givenColor[1], givenColor[2])
    else:
        print("getColorBoundingBox given bad value")
        print("given:")
        print(givenColor)
        exit()
        return (BLACK[0], BLACK[1], BLACK[2], BLACK[0], BLACK[1], BLACK[2])
