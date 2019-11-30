import concurrent.futures
import time
import numpy


# get the squared difference to another color
def getColorDiff(targetColor_A, targetColor_B):
    colorDiff = numpy.subtract(targetColor_A, targetColor_B)
    colorDiffSquared = numpy.multiply(colorDiff, colorDiff)
    colorDiffSquaredSum = numpy.sum(colorDiffSquared)
    return numpy.sqrt(colorDiffSquaredSum)


# generate all colors of the color space, then shuffle the resulting array
def generateColors(COLOR_BIT_DEPTH, useMulti, useShuffle):
    valuesPerChannel = 2**COLOR_BIT_DEPTH
    totalColors = valuesPerChannel**3
    allColors = numpy.zeros([totalColors, 3], numpy.uint8)

    # Info Print
    beginTime = time.time()
    print("Generating colors... {:3.2f}".format(
        0) + '%' + " complete.", end='\r')

    # choose single or multi processing
    if (useMulti):
        allColors = generateColorsMulti(
            COLOR_BIT_DEPTH, valuesPerChannel, totalColors)
    else:
        allColors = generateColorsSingle(
            COLOR_BIT_DEPTH, valuesPerChannel, totalColors)

    # Info Print
    elapsedTime = time.time() - beginTime
    print("Generating colors... {:3.2f}".format(
        100) + '%' + " complete.", end='\n')
    print("Generated {} colors in {:3.2f} seconds.".format(
        totalColors, elapsedTime))

    if (useShuffle):
        # shuffle and return the color list
        beginTime = time.time()
        print("Shuffling colors...", end='\r')
        numpy.random.shuffle(allColors)
        elapsedTime = time.time() - beginTime
        print("Shuffled {} colors in {:3.2f} seconds.".format(
            totalColors, elapsedTime))

    return allColors


# DEBUG
# def generateColors(COLOR_BIT_DEPTH, useMulti, useShuffle):
#     return numpy.array([[255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 0, 0],
#                         [0, 255, 0],
#                         [0, 0, 255],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [255, 255, 0],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [0, 255, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 0, 255],
#                         [255, 175, 0],
#                         [255, 175, 0],
#                         [255, 175, 0],
#                         [255, 175, 0],
#                         [255, 175, 0],
#                         [0, 255, 175],
#                         [0, 255, 175],
#                         [0, 255, 175],
#                         [0, 255, 175],
#                         [0, 255, 175],
#                         [175, 0, 255],
#                         [175, 0, 255],
#                         [175, 0, 255],
#                         [175, 0, 255],
#                         [175, 0, 255],
#                         [175, 175, 175]])


# generate all colors of the color space, don't use multiprocessing
def generateColorsSingle(COLOR_BIT_DEPTH, valuesPerChannel, totalColors):
    allColors = numpy.zeros([totalColors, 3], numpy.uint8)

    index = 0
    # loop over all r,g,b values
    for r in range(valuesPerChannel):
        for g in range(valuesPerChannel):
            for b in range(valuesPerChannel):
                # insert the color in its place
                allColors[index] = numpy.array([r, g, b], numpy.uint8)
                index += 1

        print("Generating colors... {:3.2f}".format(
            100*r/valuesPerChannel) + '%' + " complete.", end='\r')

    # generation completed
    return allColors


# generate all colors of the color space, use multiprocessing
def generateColorsMulti(COLOR_BIT_DEPTH, valuesPerChannel, totalColors):
    allColors = numpy.zeros([totalColors, 3], numpy.uint8)

    # using multiprocessing kick off a worker for each red value in range of red values
    generator = concurrent.futures.ProcessPoolExecutor()
    constantReds = [generator.submit(
        generateColors_worker, red, valuesPerChannel) for red in range(valuesPerChannel)]

    # for each worker as it completes, insert its results into the array
    # the order that this happens does not matter as the array will be shuffled anywasys
    index = 0
    for constantRed in concurrent.futures.as_completed(constantReds):
        allColors[index * (valuesPerChannel**2): (index + 1)
                  * (valuesPerChannel**2)] = constantRed.result()
        index += 1
        print("Generating colors... {:3.2f}".format(
            100*index/valuesPerChannel) + '%' + " complete.", end='\r')

    # generation completed
    return allColors


# for a given red value generate every color possible with the remaing green and blue values
def generateColors_worker(r, valuesPerChannel):
    workerColors = numpy.zeros([valuesPerChannel**2, 3], numpy.uint8)

    index = 0
    # loop over every value of green and blue producing each color that can have the given red value
    for g in range(valuesPerChannel):
        for b in range(valuesPerChannel):
            # insert the color in its place
            workerColors[index] = numpy.array([r, g, b], numpy.uint8)
            index += 1

    # return all colors with the given red value
    return workerColors
