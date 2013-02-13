#!/usr/bin/env python
"""Simple test case with no jumpers required."""

import optparse
import os
import sys
import unittest

import buildmap

def FindFile(path_list):
  for pp in path_list:
    if os.path.exists(pp):
      return pp
      break
  return None

# Note: bluetooth address must be passed in throught IOIO
class BuildmapTests(unittest.TestCase):

  def testOpen(self):
    pin_path = FindFile(('pins.txt', '../pins.txt'))
    self.assertTrue(pin_path != None, "Could not find pins.txt")
    out_file = "/tmp/pin_map.py" # BUG: not user or OS independent
    if os.path.exists(out_file):
      os.remove(out_file)
    self.assertFalse(os.path.exists(out_file))

    parser = optparse.OptionParser(usage="Usage: buildmap infile [outfile]")
    parser.add_option("-n", "--name", dest="name",
                    help="Name of array to create", default="PIN_FUNCTION")
    (options, args) = parser.parse_args([])

    buildmap.ParseFile(open(pin_path), pin_path, open(out_file, "w"), options)
    # TODO: diff new file against usual file

if __name__ == "__main__":
    unittest.main()
