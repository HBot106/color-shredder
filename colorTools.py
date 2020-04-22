import concurrent.futures
import time
import numpy
import colorsys
import config

# generate all colors of the color space, then shuffle the resulting array

COLOR_BIT_DEPTH = config.PARSED_ARGS.c
VALUES_PER_CHANNEL = 2**COLOR_BIT_DEPTH
NUMBER_SUB_COLORS = VALUES_PER_CHANNEL**2
NUMBER_ALL_COLORS = VALUES_PER_CHANNEL**3

USE_SHUFFLE = config.PARSED_ARGS.x
HLS = config.PARSED_ARGS.hls
HSV = config.PARSED_ARGS.hsv

def generateColors():
    # Setup
    list_of_all_colors = numpy.zeros([((2**COLOR_BIT_DEPTH)**3), 3], numpy.uint16)

    hues = numpy.array(range((2**COLOR_BIT_DEPTH)))
    numpy.random.shuffle(hues)

    # using multiprocessing kick off a worker for each chan1_val value in range of chan1_val values
    process_pool_executor = concurrent.futures.ProcessPoolExecutor()
    process_pool_results = [process_pool_executor.submit(colorWorker, chan1_val) for chan1_val in hues]

    # for each worker as it completes, insert its results into the array
    # the order that this happens does not matter as the array will be shuffled anywasys
    index_in_color_list = 0
    for color_sub_list in concurrent.futures.as_completed(process_pool_results):
        list_of_all_colors[index_in_color_list * NUMBER_SUB_COLORS: (index_in_color_list + 1) * NUMBER_SUB_COLORS] = color_sub_list.result()
        index_in_color_list += 1
        print("Generating colors... {:3.2f}".format(100*index_in_color_list/(2**COLOR_BIT_DEPTH)) + '%' + " complete.", end='\r')

    if (USE_SHUFFLE):
        numpy.random.shuffle(list_of_all_colors)

    return list_of_all_colors


# for a given chan1_val value generate every color possible with the remaing chan3_val and chan2_val values
def colorWorker(chan1_val):

    # Setup
    color_sub_list = numpy.zeros([VALUES_PER_CHANNEL**2, 3], numpy.uint16)
    index_in_color_sub_list = 0
    output_color = [0,0,0]
    channel_shift = 1

    # loop over every value of chan3_val and chan2_val producing each color that can have the given chan1_val
    for chan2_val in range(VALUES_PER_CHANNEL):
        for chan3_val in range(VALUES_PER_CHANNEL):
            # insert the color in its place

            output_color[(0 + channel_shift) % 3] = chan1_val / VALUES_PER_CHANNEL
            output_color[(1 + channel_shift) % 3] = chan2_val / VALUES_PER_CHANNEL
            output_color[(2 + channel_shift) % 3] = chan3_val / VALUES_PER_CHANNEL

            if (HLS):
                rgb_color = colorsys.hls_to_rgb((output_color[0]), (output_color[1]), (output_color[2]))
            elif (HSV):
                rgb_color = colorsys.hsv_to_rgb((output_color[0]), (output_color[1]), (output_color[2]))
            else:
                rgb_color = ((output_color[0]), (output_color[1]), (output_color[2]))

            color_sub_list[index_in_color_sub_list] = numpy.array([(rgb_color[0] * 255), (rgb_color[1] * 255), (rgb_color[2] * 255)], numpy.uint16)
            index_in_color_sub_list += 1

    # return all colors with the given chan1_val value
    numpy.random.shuffle(color_sub_list)
    return color_sub_list