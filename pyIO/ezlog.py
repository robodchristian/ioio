# Copyright 2012 Google Inc. All rights reserved

# Dan Christian
# 27 Sept 2012

"""Simple logging with a global outfile and debug level.

Usage:
import ezlog
Debug = ezlog.Debug
Info  = ezlog.Info
Warn  = ezlog.Warn
Error  = ezlog.Error

ezlog.LogLevel(ezlog.NOTICE)
Info("Good to know")
"""

import sys, time

# The log level is just a number.  Higher is more verbose.
# These constants are just suggestions.
# They are spaced so you can do extras in between.
ERROR, WARN, INFO, DEBUG = range(0, 40, 10)

_logfile = sys.stderr
_loglevel = WARN
_logTime = None                 # time offset (seconds)

def Debug(msg):
  """Log a Debug level message."""
  LogMsg(DEBUG, msg)


def Info(msg):
  """Log a Information level message."""
  LogMsg(INFO, msg)


def Warn(msg):
  """Log a Warning level message."""
  LogMsg(WARN, msg)


def Error(msg):
  """Log a Error level message."""
  LogMsg(ERROR, msg)


def LogMsg(threshold, msg):
  """Log a message if threshold <= current log level"""
  if threshold <= _loglevel:
    if _logTime is not None:
      print >> _logfile, "(%.3f)%s" % (time.time() - _logTime, msg)
    else:
      print >> _logfile, msg


def WouldLog(threshold):
  """Return true if threshold would be sent to the log."""
  return (threshold <= _loglevel)


def LogLevel(level):
  """Set the logging display level.

  Accepts a number, a string the converts to a number, or one of the
  above strings."""
  global _loglevel
  try:
    _loglevel = int(level)
    return
  except ValueError:
    pass
  if level.upper().startswith('DEBUG'):
    _loglevel = DEBUG
  elif level.upper().startswith('INFO'):
    _loglevel = INFO
  elif level.upper().startswith('WARN'):
    _loglevel = WARN
  elif level.upper().startswith('ERROR'):
    _loglevel = ERROR


def LogTime(start_time):
  """Enable/disable timestamps.

  start_time can be one of the following:
    True - get current time and use as time offset
    False or None - disable timestamp
    time in seconds to subtract from timestamp
  """
  global _logTime

  if start_time is True:        # use current time as start time
    _logTime = time.time()
  elif start_time in (False, None):
    _logTime = None
  else:
    _logTime = start_time


def LogFile(file_obj):
  """Set the logging output object.

  If None, set output to stderr.
"""
  global _logfile
  if file_obj is not None:
    _logfile = file_obj
  else:
    _logfile = sys.stderr
