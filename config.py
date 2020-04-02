import os
import numpy

mode = dict(
    MIN = 0,
    AVG = 1,
    FAST = 2,
    CURRENT = 1,
    DEFAULT = 2
)

color = dict(
    SHUFFLE = True,
    MULTIPROCESSING = True
)

painter = dict(
    LOCATIONS_PER_PAINTER = 50,
    MIN_MULTI_WORKLOAD = 200,
    PRINT_RATE = 1,
    DEBUG_WAIT = True
)

canvas = dict(
    COLOR_BIT_DEPTH = 6,
    CANVAS_WIDTH = 32,
    CANVAS_HEIGHT = 32,
    START_X = 16,
    START_Y = 16
)
