import concurrent.futures
import time
import numpy

# BLACK reference
BLACK = numpy.array([0, 0, 0], numpy.uint32)


# get the squared difference to another color
def getColorDiff(targetColor_A, targetColor_B):

    rgb_color_difference = numpy.array([0, 0, 0], numpy.uint32)
    rgb_difference_squared = numpy.array([0, 0, 0], numpy.uint32)
    sum_of_squared_values = numpy.uint32

    # use the euclidian distance formula over [R,G,B] instead of [X,Y,Z]
    rgb_color_difference = numpy.subtract(targetColor_A, targetColor_B)
    rgb_difference_squared = numpy.multiply(rgb_color_difference, rgb_color_difference)
    sum_of_squared_values = numpy.sum(rgb_difference_squared)

    # to get distance the sqrt must be taken, but we don't care about the actual distance, just relative distances, so we skip the sqrt for a constant runtime improvement
    # return numpy.sqrt(sum_of_squared_values)
    return sum_of_squared_values


# generate all colors of the color space, then shuffle the resulting array
def generateColors(COLOR_BIT_DEPTH, use_multiprocessing, use_shuffle):

    # Setup, how many colors are needed?
    values_per_color_channel = 2**COLOR_BIT_DEPTH
    count_total_colors = values_per_color_channel**3
    list_of_all_colors = numpy.zeros([count_total_colors, 3], numpy.uint32)

    # Info Print
    time_start = time.time()
    print("Generating colors... {:3.2f}".format(0) + '%' + " complete.", end='\r')

    # choose single or multi processing
    if (use_multiprocessing):
        list_of_all_colors = generateColorsMulti(COLOR_BIT_DEPTH, values_per_color_channel, count_total_colors)
    else:
        list_of_all_colors = generateColorsSingle(COLOR_BIT_DEPTH, values_per_color_channel, count_total_colors)

    # Info Print
    time_elapsed = time.time() - time_start
    print("Generating colors... {:3.2f}".format(100) + '%' + " complete.", end='\n')
    print("Generated {} colors in {:3.2f} seconds.".format(count_total_colors, time_elapsed))

    # Suffle the color list, so it is in a random order
    if (use_shuffle):
        time_start = time.time()
        print("Shuffling colors...", end='\r')
        numpy.random.shuffle(list_of_all_colors)
        time_elapsed = time.time() - time_start
        print("Shuffled {} colors in {:3.2f} seconds.".format(count_total_colors, time_elapsed))

    return list_of_all_colors


# generate all colors of the color space, don't use multiprocessing
def generateColorsSingle(COLOR_BIT_DEPTH, values_per_color_channel, count_total_colors):

    # Setup
    rgb_working_color = numpy.zeros([1, 3], numpy.uint32)
    list_of_all_colors = numpy.zeros([count_total_colors, 3], numpy.uint32)
    index_in_color_list = 0

    # Generate all colors by looping over all r,g,b values
    for r in range(values_per_color_channel):
        for g in range(values_per_color_channel):
            for b in range(values_per_color_channel):
                # insert the color in its place
                rgb_working_color = numpy.array([
                    int((r / values_per_color_channel) * 255),
                    int((g / values_per_color_channel) * 255),
                    int((b / values_per_color_channel) * 255)], numpy.uint32)
                list_of_all_colors[index_in_color_list] = rgb_working_color
                index_in_color_list += 1

        # Info Print
        print("Generating colors... {:3.2f}".format(100*r/values_per_color_channel) + '%' + " complete.", end='\r')

    # generation completed
    return list_of_all_colors


# generate all colors of the color space, use multiprocessing
def generateColorsMulti(COLOR_BIT_DEPTH, values_per_color_channel, count_total_colors):

    # Setup
    list_of_all_colors = numpy.zeros([count_total_colors, 3], numpy.uint32)

    # using multiprocessing kick off a worker for each red value in range of red values
    process_pool_executor = concurrent.futures.ProcessPoolExecutor()
    process_pool_results = [process_pool_executor.submit(generateColors_worker, red, values_per_color_channel) for red in range(values_per_color_channel)]

    # for each worker as it completes, insert its results into the array
    # the order that this happens does not matter as the array will be shuffled anywasys
    index_in_color_list = 0
    for list_of_constant_red_colors in concurrent.futures.as_completed(process_pool_results):
        list_of_all_colors[index_in_color_list * (values_per_color_channel**2): (index_in_color_list + 1) * (values_per_color_channel**2)] = list_of_constant_red_colors.result()
        index_in_color_list += 1
        print("Generating colors... {:3.2f}".format(100*index_in_color_list/values_per_color_channel) + '%' + " complete.", end='\r')

    # generation completed
    return list_of_all_colors


# for a given red value generate every color possible with the remaing green and blue values
def generateColors_worker(r, values_per_color_channel):

    # Setup
    list_of_constant_red_colors = numpy.zeros([values_per_color_channel**2, 3], numpy.uint32)
    rgb_working_color = numpy.zeros([1, 3], numpy.uint32)
    index_in_color_list = 0

    # loop over every value of green and blue producing each color that can have the given red value
    for g in range(values_per_color_channel):
        for b in range(values_per_color_channel):
            # insert the color in its place
            rgb_working_color = numpy.array([
                numpy.uint32((r / values_per_color_channel) * 255),
                numpy.uint32((g / values_per_color_channel) * 255),
                numpy.uint32((b / values_per_color_channel) * 255)], numpy.uint32)
            list_of_constant_red_colors[index_in_color_list] = rgb_working_color
            index_in_color_list += 1

    # return all colors with the given red value
    return list_of_constant_red_colors

# turn a given color into its bounding box representation
# numpy[r,g,b] -> (r,r,g,g,b,b)


def getColorBoundingBox(rgb_requested_color):
    if (rgb_requested_color.size == 3):
        return (rgb_requested_color[0], rgb_requested_color[1], rgb_requested_color[2], rgb_requested_color[0], rgb_requested_color[1], rgb_requested_color[2])
    else:
        print("getColorBoundingBox given bad value")
        print("given:")
        print(rgb_requested_color)
        exit()