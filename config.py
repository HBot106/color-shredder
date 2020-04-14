import os
import numpy
import argparse

MODES = dict(
    MIN = 1,
    AVG = 2,
    FAST = 3,
    DEFAULT = 3
)

DEFAULT_MODE = dict(
    GET_BEST_POSITION_MODE = MODES['DEFAULT'],
    USE_NUMBA = False
)

DEFAULT_COLOR = dict(
    COLOR_BIT_DEPTH = 6,
    SHUFFLE = True,
    MULTIPROCESSING = True
)

DEFAULT_PAINTER = dict(
    LOCATIONS_PER_PAINTER = 50,
    MIN_MULTI_WORKLOAD = 200,
    MULTIPROCESSING = False,
    MAX_PAINTERS = (os.cpu_count() * 2),
    PRINT_RATE = 25,
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


# Arguments
CONFIG_PARSER = argparse.ArgumentParser(
    description="Description",
    epilog="Epilogue",
    allow_abbrev=False
)
CONFIG_PARSER.add_argument('-m', action='store_true', help='enable multiprocessing for painting', default=DEFAULT_PAINTER['MULTIPROCESSING'])
CONFIG_PARSER.add_argument('-j', action='store_true', help='enable just in time compilation for painting', default=DEFAULT_MODE['USE_NUMBA'])
CONFIG_PARSER.add_argument('-c', metavar='depth', help='color space bit depth', default=DEFAULT_COLOR['COLOR_BIT_DEPTH'], type=int)
CONFIG_PARSER.add_argument('-d', metavar='dim', nargs=2, help='dimensions of the output image', default=[DEFAULT_CANVAS['CANVAS_WIDTH'], DEFAULT_CANVAS['CANVAS_HEIGHT']], type=int)
CONFIG_PARSER.add_argument('-s', metavar='coord', nargs=2, help='coordinates of the starting location', default=[DEFAULT_CANVAS['START_X'], DEFAULT_CANVAS['START_Y']], type=int)
CONFIG_PARSER.add_argument('-f', metavar='filename', help='name of output image', default=DEFAULT_PAINTER['PAINTING_NAME'], type=str)
CONFIG_PARSER.add_argument('-r', metavar='rate', help='info print and update painting at this pixel rate', default=DEFAULT_PAINTER['PRINT_RATE'], type=int)
CONFIG_PARSER.add_argument('-q', metavar='strategy', choices=[1, 2, 3], help='strategy for choosing best location: min:0, avg:1, or quick:2', default=DEFAULT_MODE['GET_BEST_POSITION_MODE'], type=int)
PARSED_ARGS = CONFIG_PARSER.parse_args()