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
    PRINT_RATE=10
)

canvas = dict(
    COLOR_BIT_DEPTH=6,
    CANVAS_WIDTH=128,
    CANVAS_HEIGHT=128,
    START_X=64,
    START_Y=64
)
