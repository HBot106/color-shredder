import os
import numpy
import argparse

modes = dict(
    MIN = 0,
    AVG = 1,
    FAST = 2,
    DEFAULT = 1
)

mode = dict(
    GET_BEST_POSITION_MODE = modes['DEFAULT'],
    BOOL_USE_NUMBA = True
)

color = dict(
    SHUFFLE = True,
    MULTIPROCESSING = True
)

painter = dict(
    LOCATIONS_PER_PAINTER = 50,
    MIN_MULTI_WORKLOAD = 200,
    MULTIPROCESSING = False,
    MAX_PAINTERS = (os.cpu_count() * 2),
    PRINT_RATE = 100,
    DEBUG_WAIT = False,
    DEBUG_WAIT_TIME = 1,
    PAINTING_NAME = "painting"
)

canvas = dict(
    COLOR_BIT_DEPTH = 6,
    CANVAS_WIDTH = 100,
    CANVAS_HEIGHT = 100,
    START_X = 50,
    START_Y = 50
)


# Arguments
arg_parser = argparse.ArgumentParser(
    description="Description",
    epilog="Epilogue",
    allow_abbrev=False
)
arg_parser.add_argument('-m', action='store_true', help='enable multiprocessing for painting', default=False)
arg_parser.add_argument('-j', action='store_true', help='enable just in time compilation for painting', default=False)
arg_parser.add_argument('-c', metavar='depth', help='color space bit depth', default=6)
arg_parser.add_argument('-d', metavar='dim', nargs=2, help='dimensions of the output image', default=canvas['CANVAS_WIDTH'])
arg_parser.add_argument('-s', metavar='coord', nargs=2, help='coordinates of the starting location', default=canvas['START_X'])
arg_parser.add_argument('-f', metavar='filename', help='name of output image', default=painter['PAINTING_NAME'])
arg_parser.add_argument('-p', metavar='rate', help='info print and update painting at this pixel rate', default=painter['PRINT_RATE'])
arg_parser.add_argument('-q', metavar='strat', choices=['min', 'avg', 'quick'], help='strategy for choosing best location: min, avg, or quick', default='avg')
parsed_args = arg_parser.parse_args()