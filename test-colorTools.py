import concurrent.futures
import time
import numpy

import unittest

import colorTools

BLACK = numpy.array([0, 0, 0])
RED = numpy.array([255, 0, 0])
GREEN = numpy.array([0, 255, 0])
BLUE = numpy.array([0, 0, 255])


class TestColorTools(unittest.TestCase):

    def testGetColorDiff_blackBlack(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLACK), numpy.array(BLACK))//1, 0)

    def testGetColorDiff_blackRed(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLACK), numpy.array(RED))//1, 255)

    def testGetColorDiff_blackGreen(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLACK), numpy.array(GREEN))//1, 255)

    def testGetColorDiff_blackBlue(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLACK), numpy.array(BLUE))//1, 255)
# =============================================================================

    def testGetColorDiff_redBlack(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(RED), numpy.array(BLACK))//1, 255)

    def testGetColorDiff_redRed(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(RED), numpy.array(RED))//1, 0)

    def testGetColorDiff_redGreen(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(RED), numpy.array(GREEN))//1, 360)

    def testGetColorDiff_redBlue(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(RED), numpy.array(BLUE))//1, 360)
# =============================================================================


    def testGetColorDiff_greenBlack(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(GREEN), numpy.array(BLACK))//1, 255)

    def testGetColorDiff_greenRed(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(GREEN), numpy.array(RED))//1, 360)

    def testGetColorDiff_greenGreen(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(GREEN), numpy.array(GREEN))//1, 0)

    def testGetColorDiff_greenBlue(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(GREEN), numpy.array(BLUE))//1, 360)
# =============================================================================


    def testGetColorDiff_blueBlack(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLUE), numpy.array(BLACK))//1, 255)

    def testGetColorDiff_blueRed(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLUE), numpy.array(RED))//1, 360)

    def testGetColorDiff_blueGreen(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLUE), numpy.array(GREEN))//1, 360)

    def testGetColorDiff_blueBlue(self):
        self.assertEqual(colorTools.getColorDiff(
            numpy.array(BLUE), numpy.array(BLUE))//1, 0)


if __name__ == '__main__':
    unittest.main()
