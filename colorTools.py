import concurrent.futures
import time
import numpy


# get the squared difference to another color
def getColorDifferenceSquared(check_color1, check_color2):
    # I figure for minimization purposes distance^2 is just as good as distance
    r_comp = check_color1[0] - check_color2[0]
    g_comp = check_color1[1] - check_color2[1]
    b_comp = check_color1[2] - check_color2[2]
    return (r_comp * r_comp) + (g_comp * g_comp) + (b_comp * b_comp)


# generate all colors of the color space and randomize their order
def generateColors(COLOR_BIT_DEPTH):
    beginTime = time.time()

    # calculate number of values per channel (256 for 8 bit)
    valuesPerChannel = 2**COLOR_BIT_DEPTH
    # calculate the total number of colors ( 256^3 (~16 Million) for 8 bit)
    totalColors = valuesPerChannel**3

    # create zeroed array of propper size
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

    # Print Summary
    elapsedTime = time.time() - beginTime
    print("Generated {} colors in {:3.2f} seconds.".format(totalColors, elapsedTime))

    # shuffle and return the color list
    return numpy.random.shuffle(allColors)


# for a given red value generate every color possible with the remaing green and blue values
def generateColors_worker(r, valuesPerChannel):

    # create zeroed array of propper size
    workerColors = numpy.zeros([valuesPerChannel**2, 3], numpy.uint8)

    # loop over every value of green and blue producing each color that can have the given red value
    for g in range(valuesPerChannel):
        for b in range(valuesPerChannel):
            # insert the color in its place
            workerColors[g * b] = numpy.array([r, g, b], numpy.uint8)

    # return all colors with the given red value
    return workerColors
