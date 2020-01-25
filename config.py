import os
import numpy

output = dict(
    FILENAME="painting"
)

mode = dict(
    MIN=0,
    AVG=1,
    FAST=2,
    CURRENT=2,
    DEFAULT=2
)

color = dict(
    SHUFFLE=True,
    MULTIPROCESSING=True
)

painter = dict(
    LOCATIONS_PER_PAINTER=50,
    MIN_MULTI_WORKLOAD=200,
    PRINT_RATE=200
)

canvas = dict(
    COLOR_BIT_DEPTH=8,
    CANVAS_WIDTH=256,
    CANVAS_HEIGHT=256,
    START_X=0,
    START_Y=0
)
