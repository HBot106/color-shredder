import colorTools

import sys
import numpy

import unittest

import canvasTools

# BLACK reference
BLACK = numpy.zeros(3, numpy.uint8)





class TestCanvasTools(unittest.TestCase):

    def testToRawOutput(self):
        self.assertEqual(


    def testConsiderPixelAt(self):
        self.assertEqual(


    def testGetValidNeighbors(self):
        self.assertEqual(



if __name__ == '__main__':
    unittest.main()
