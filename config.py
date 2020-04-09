import os
import numpy

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
    CANVAS_WIDTH = 64,
    CANVAS_HEIGHT = 64,
    START_X = 32,
    START_Y = 32
)
