import os
import numpy
from rtree import index as rTree

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
    PRINT_RATE=100
)

canvas = dict(
    COLOR_BIT_DEPTH=8,
    CANVAS_WIDTH=128,
    CANVAS_HEIGHT=128,
    START_X=64,
    START_Y=64
)

index_properties = rTree.Property()
index_properties.storage = rTree.RT_Memory
index_properties.dimension = 3
index_properties.variant = rTree.RT_Star
index_properties.near_minimum_overlap_factor = 32
index_properties.leaf_capacity = 32
index_properties.index_capacity = 32
index_properties.fill_factor = 0.5

spatial_index_of_neighborhood_color_holding_location = rTree.Index(properties=index_properties)
