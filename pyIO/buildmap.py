#!/usr/bin/python
# Copyright 2012 Google Inc. All rights reserved

"""Clean up the pin table from
https://github.com/ytai/ioio/wiki/Getting-To-Know-The-Board and turn
it in a python map with the data.
"""

import string, sys

# parseargs in newer, but requires python 2.7+ (or an install)
import optparse

_HEADER = '# This file was automatically generated from %s by buildmap.py\n\
# DO NOT EDIT\n\
%s = {'


def ParseFile(infile, name, outfile, options):
  labels = None
  for line in infile:
    line = line.strip()
    entries = line.split('\t')
    if not labels:              # first line is column labels
      if entries[0] != 'IOIO pin': # skip stuff before header
        print >> sys.stderr, 'Skipping', entries  # DEBUG
        continue
      entries[0] = 'pin'
      for ii in range(len(entries)):
        if entries[ii] == '5V': # label (below) can't start with a number
          entries[ii] = 'IN5V'
          continue
        entries[ii] = entries[ii].replace(' ', '_')
        entries[ii] = entries[ii].replace('/', '2')
        entries[ii] = entries[ii].replace('.', '')
        entries[ii] = str(entries[ii]).upper()
      labels = entries
      print >>outfile, _HEADER % (name, options.name)
      print >>outfile, "# %6s: (\t%s)," % (entries[0], ',\t'.join(entries[1:]))
      continue
    if entries[0].startswith('mclr'): # skip mclr
      continue
    if entries[0].startswith('stat '): # fixup 'stat LED' -> 'LED'
      entries[0] = entries[0][5:]
    for ii in range(len(entries)):
      if not entries[ii]:       # convert empty to None
        entries[ii] = 'None'
      elif not ((entries[ii][0] in string.digits)
                and (entries[ii][-1] in string.digits)):
        if entries[ii].startswith('Y (ref '): # fixup 'Y (ref +)' to 'Y/R+'
          entries[ii] = 'Y/R%s' % entries[ii][-2]
        entries[ii] = "'%s'" % entries[ii]
    print >>outfile, "  %6s: (\t%s)," % (entries[0], ',\t'.join(entries[1:]))
  print >>outfile, '}'
  if labels:
    print >>outfile, "# index names for the tuple"
    print >>outfile, ', '.join(labels[1:]), '= range(%d)' % (len(labels) - 1)


def main():
  parser = optparse.OptionParser(usage="Usage: buildmap infile [outfile]")
  parser.add_option("-n", "--name", dest="name",
                  help="Name of array to create", default="PIN_FUNCTION")
  (options, args) = parser.parse_args()
  if len(args) < 1:
    print "No file specified"
    sys.exit(2)
  elif len(args) < 2:
    ParseFile(open(args[0]), args[0], sys.stdout, options)
  elif len(args) == 2:
    if args[0] == args[1]:
      print "Input and output cannot be the same"
      sys.exit(1)
    ParseFile(open(args[0]), args[0], open(args[1], 'w'), options)
  else:
    print "Too many arguments to parse"
    sys.exit(2)


if __name__ == '__main__':
  main()
