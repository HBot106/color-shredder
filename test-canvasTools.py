import colorTools

import sys
import numpy

import unittest

import canvasTools

# BLACK reference
BLACK = numpy.array([0, 0, 0])
RED = numpy.array([255, 0, 0])
GREEN = numpy.array([0, 255, 0])
BLUE = numpy.array([0, 0, 255])


class TestCanvasTools(unittest.TestCase):

    def testToRawOutput(self):
        testInput = numpy.array([[RED, GREEN, BLUE],
                                 [RED, GREEN, BLUE],
                                 [RED, GREEN, BLUE]])
        testOutput = numpy.array([[255, 0, 0, 255, 0, 0, 255, 0, 0],
                                  [0, 255, 0, 0, 255, 0, 0, 255, 0],
                                  [0, 0, 255, 0, 0, 255, 0, 0, 255]])

        self.assertEqual(canvasTools.toRawOutput(
            testInput).all(), testOutput.all())
    # =============================================================================

    # BOOM THIS IS THE PROBLEM!!!!!!!!... i think...

    def testConsiderPixelAt(self):
        canvas = numpy.array([[RED, RED, RED],
                              [RED, BLACK, RED],
                              [RED, RED, RED]])
        self.assertEqual(canvasTools.considerPixelAt(canvas, 1, 1, RED, True), 0)
    # =============================================================================


    def testGetValidNeighbors0(self):
        # no neighbors

        # canvas =
        # R R G
        # R * G
        # B B B
        canvas=numpy.array([[RED, RED, GREEN],
                              [RED, BLACK, GREEN],
                              [BLUE, BLUE, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([]).all())

    def testGetValidNeighbors1(self):
        # 1 neighbor

        # canvas =
        # R R G
        # R * G
        # B * B
        canvas=numpy.array([[RED, RED, GREEN],
                              [RED, BLACK, GREEN],
                              [BLUE, BLACK, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([2, 1]).all())

    def testGetValidNeighbors2(self):
        # 1 neighbor

        # canvas =
        # R R G
        # R * *
        # B B B
        canvas=numpy.array([[RED, RED, GREEN],
                              [RED, BLACK, BLACK],
                              [BLUE, BLUE, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([1, 2]).all())

    def testGetValidNeighbors3(self):
        # 1 neighbor

        # canvas =
        # R R G
        # * * G
        # B B B
        canvas=numpy.array([[RED, RED, GREEN],
                              [BLACK, BLACK, GREEN],
                              [BLUE, BLUE, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([1, 0]).all())

    def testGetValidNeighbors4(self):
        # 1 neighbor

        # canvas =
        # R * G
        # R * G
        # B B B
        canvas=numpy.array([[RED, BLACK, GREEN],
                              [RED, BLACK, GREEN],
                              [BLUE, BLUE, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([0, 1]).all())

    def testGetValidNeighbors5(self):
        # 4 neighbors

        # canvas =
        # R * G
        # * * *
        # B * B
        canvas=numpy.array([[RED, BLACK, GREEN],
                              [BLACK, BLACK, BLACK],
                              [BLUE, BLACK, BLUE]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([[0, 1], [1, 0], [1, 2], [2, 1]]).all())

    def testGetValidNeighbors6(self):
        # 4 neighbors

        # canvas =
        # * R *
        # R * G
        # * B *
        canvas=numpy.array([[BLACK, RED, BLACK],
                              [RED, BLACK, GREEN],
                              [BLACK, BLUE, BLACK]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([[0, 0], [0, 2], [2, 0], [2, 2]]).all())

    def testGetValidNeighbors7(self):
        # 8 neighbors

        # canvas =
        # * * *
        # * * *
        # * * *
        canvas=numpy.array([[BLACK, BLACK, BLACK],
                              [BLACK, BLACK, BLACK],
                              [BLACK, BLACK, BLACK]])

        self.assertEqual(canvasTools.getValidNeighbors(
            canvas, 1, 1).all(), numpy.array([[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2], ]).all())


if __name__ == '__main__':
    unittest.main()
