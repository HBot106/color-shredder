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


# dispatches workers to generate a list of all colors of a color space in a random order
# generates all colors in the 8 bit rgb color space using worlkers
def generateColors(COLOR_BIT_DEPTH):

    # results holds the processes that we need to get a result from
    results = []
    # the worker reults are combined into allColors
    allColors = []
    # the number of integer values for each color channel (256 for 8 bit)
    numberOfChannelValues = 2**COLOR_BIT_DEPTH
    # the number of chunks to split the color space generation into
    split = 8

    # Manage Color Genetration
    print("Generating All Colors: " + str(0) + "% ...", end='\r')
    start = time.time()

    # Using a ProcessPoolExecutor dispatch workers to generate sections of the color space
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # get the list of workers, giving each a different index
        results = [executor.submit(
            generateColors_worker, index, split, numberOfChannelValues) for index in range(split)]

        # for each worker as it finishes, add its result to allColors
        # allColors is going to be shuffled anyways, so the order the workers finish is irrelevent
        for red in concurrent.futures.as_completed(results):
            allColors += red.result()
            # print completion progress
            print("Generating All Colors: " + str(len(allColors) *
                                                  100//numberOfChannelValues**3) + "% ...", end='\r')

    elapsed = time.time() - start
    print('\n' + "Colors generated in: " + str(elapsed) + " seconds.")

    # shuffle the list of colors
    print("Shuffling...")
    start = time.time()
    # 5x speed increase going from random.shuffle() to numpy.random.shuffle()
    numpy.random.shuffle(allColors)
    elapsed = time.time() - start
    print("Shuffling Complete, " + str(len(allColors)) +
          "colors in " + str(elapsed) + " seconds.")

    return(allColors)


# worker for the generation of all the colors
def generateColors_worker(index, split, numberOfChannelValues):
    workerResult = []
    color = []

    # for the size of the red split:
    for r in range(numberOfChannelValues//split):
        # for all values of green and blue:
        for g in range(numberOfChannelValues):
            for b in range(numberOfChannelValues):
                    # add each color
                    # red is determined by the ((index of split * size of split) + index in split)
                color = [((index * (numberOfChannelValues//split)) + r), g, b]
                workerResult.append(color)
    return workerResult
