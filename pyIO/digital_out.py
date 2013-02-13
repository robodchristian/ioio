# Copyright 2012 Google Inc. All rights reserved

"""Digital output pin support for IOIO
"""

import threading

import exception

import ezlog
Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error


# output modes
MODE_NORMAL, MODE_OPEN_DRAIN = range(2)

class DigitalOutput(object):
  """Digital output pin object.

  Interface to pin and handle callbacks on incoming data
  """

  def __init__(self, ioio, pin, mode, start_value):
    self.ioio = ioio               # top level interface
    self.pin = pin                 # pin number
    self.event = threading.Event() # flag for new data
    self.state = start_value       # state
    self.mode = mode               # open-drain or not

    self.ioio.proto.CheckState()
    self.ioio.proto._SetPinDigitalOut(self.pin, self.mode, start_value)

  def __del__(self):
    """We need to break back references so garbage collection can work."""
    # un-register handlers
    if not self.ioio:
      return
    self.ioio.pins.FreePin(self.pin)
    self.ioio._ForgetSub(self)  # tell parent to forget about us
    self.ioio = None            # remove circular link

  def Close(self):              # close object
    self.__del__()

  def Write(self, level):
    if not self.ioio:
      raise exception.ConnectionLostException
    else:
      self.ioio.proto.CheckState()
    self.event.clear()
    self.ioio.proto._SetDigitalOutLevel(self.pin, level)
