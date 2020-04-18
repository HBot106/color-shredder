import os
import numpy
import argparse
import rtree


MODES = dict(
    MIN = 1,
    AVG = 2,
    FAST = 3,
    DEFAULT = 3
)

DEFAULT_MODE = dict(
    GET_BEST_POSITION_MODE = MODES['DEFAULT'],
    USE_NUMBA = False,
    USE_RTREE = False
)

DEFAULT_COLOR = dict(
    COLOR_BIT_DEPTH = 6,
    SHUFFLE = True,
    MULTIPROCESSING = True
)

DEFAULT_PAINTER = dict(
    LOCATIONS_PER_PAINTER = 100,
    MIN_MULTI_WORKLOAD = 100,
    MULTIPROCESSING = False,
    MAX_PAINTERS = (os.cpu_count()),
    PRINT_RATE = 100,
    DEBUG_WAIT = False,
    DEBUG_WAIT_TIME = 1,
    PAINTING_NAME = "painting"
)

DEFAULT_CANVAS = dict(
    CANVAS_WIDTH = 64,
    CANVAS_HEIGHT = 64,
    START_X = 0,
    START_Y = 0
)

print("")

# Arguments
CONFIG_PARSER = argparse.ArgumentParser(
    description="The Color Shredder chooses colors from a randomized set, placing colors one at a time in the location where the color \"fits best\". There are three available strategies for best fit. The process can also be accelerated with CPU Parallelism, Just-In-Time Compilation, OpenCL Parallelism, or a Spatial Data Structure.",
    allow_abbrev=False
)
CONFIG_PARSER.add_argument('-m', action='store_true', help='enable multiprocessing for painting', default=DEFAULT_PAINTER['MULTIPROCESSING'])
CONFIG_PARSER.add_argument('-j', action='store_true', help='enable just in time compilation for painting', default=DEFAULT_MODE['USE_NUMBA'])
CONFIG_PARSER.add_argument('-t', action='store_true', help='use rTree for painting', default=DEFAULT_MODE['USE_RTREE'])
CONFIG_PARSER.add_argument('-c', metavar='dep', help='color space bit depth', default=DEFAULT_COLOR['COLOR_BIT_DEPTH'], type=int)
CONFIG_PARSER.add_argument('-d', metavar='dim', nargs=2, help='dimensions of the output image', default=[DEFAULT_CANVAS['CANVAS_WIDTH'], DEFAULT_CANVAS['CANVAS_HEIGHT']], type=int)
CONFIG_PARSER.add_argument('-s', metavar='crd', nargs=2, help='coordinates of the starting location', default=[DEFAULT_CANVAS['START_X'], DEFAULT_CANVAS['START_Y']], type=int)
CONFIG_PARSER.add_argument('-f', metavar='flnm', help='name of output image', default=DEFAULT_PAINTER['PAINTING_NAME'], type=str)
CONFIG_PARSER.add_argument('-r', metavar='rte', help='info print and update painting at this pixel rate', default=DEFAULT_PAINTER['PRINT_RATE'], type=int)
CONFIG_PARSER.add_argument('-q', metavar='strt', choices=[1, 2, 3], help='strategy for choosing best location: min:0, avg:1, or quick:2', default=DEFAULT_MODE['GET_BEST_POSITION_MODE'], type=int)
PARSED_ARGS = CONFIG_PARSER.parse_args()

print("")
if (PARSED_ARGS.t and PARSED_ARGS.m):
    print("Cannot use -m and -t together")
    quit()
if (PARSED_ARGS.t and PARSED_ARGS.j):
    print("Cannot use -j and -t together")
    quit()
if (PARSED_ARGS.t and not (PARSED_ARGS.q == 3)):
    print("When using the rTree, shredder can only utilize the quick strategy")
    quit()
PARSED_ARGS.r = max(PARSED_ARGS.r, DEFAULT_PAINTER['MAX_PAINTERS'])


# rTree properties
index_properties = rtree.index.Property()
index_properties.storage = rtree.index.RT_Memory
index_properties.dimension = 3
index_properties.variant = rtree.index.RT_Star
index_properties.near_minimum_overlap_factor = 32
index_properties.leaf_capacity = 32
index_properties.index_capacity = 32
index_properties.fill_factor = 0.5