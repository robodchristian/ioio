# Copyright 2012 Google Inc. All rights reserved

"""Digital input pin support for IOIO
"""

import time
import threading

import exception

import ezlog
Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error


# Input termination modes:  No resistor, internal pull up, internal pull down
MODE_FLOATING, MODE_PULL_UP, MODE_PULL_DOWN = range(3)

class DigitalInput(object):
  """Digital input pin object.

  Handle callbacks with incoming data
  """

  def __init__(self, ioio, pin, mode=MODE_FLOATING):
    self.ioio = ioio               # top level interface
    self.pin = pin                 # pin number
    self.mode = mode               # pull up mode
    self.event = threading.Event() # flag for new data
    self.state = None              # state
    self.notify = None             # set if changenotify on

    self.ioio.proto.CheckState()
    # register handlers
    self.ioio.proto._RegisterHandler('HandleSetChangeNotify', self.pin,
                                self._HandleSetChangeNotify)
    self.ioio.proto._RegisterHandler('HandleReportDigitalInStatus', self.pin,
                                self._HandleReportDigitalInStatus)
    self.ioio.proto._SetPinDigitalIn(self.pin, self.mode)
    self.ioio.proto._SetChangeNotify(self.pin, True);

  def __del__(self):
    """We need to break back references so garbage collection can work."""
    # un-register handlers
    if not self.ioio:
      return
    if self.ioio.proto.IsConnected:
      self.ioio.proto._SetChangeNotify(self.pin, False);
    self.ioio.proto._UnregisterHandler('HandleSetChangeNotify', self.pin,
                                       self._HandleSetChangeNotify)
    self.ioio.proto._UnregisterHandler('HandleReportDigitalInStatus', self.pin,
                                       self._HandleReportDigitalInStatus)
    self.ioio.pins.FreePin(self.pin)
    self.ioio._ForgetSub(self)  # tell parent to forget about us
    self.ioio = None            # remove circular link

  def Close(self):   # close object
    self.__del__()

  def Read(self, timeout=5):
    """Return current input state."""
    if not self.ioio:
      raise exception.ConnectionLostException
    else:
      self.ioio.proto.CheckState()
    # ChangeNotify has been keeping us informed
    end = time.time() + timeout
    while (self.state is None) and (time.time() < end):
      time.sleep(0.01)
    return self.state

  def WaitForValue(self, value, timeout=None):
    """Wait until input is value.
    If timeout is hit, return None.
    else return value"""
    if not self.ioio:
      raise exception.ConnectionLostException
    else:
      self.ioio.proto.CheckState()
    # ChangeNotify has been keeping us informed
    if (self.state == value):
      return value
    if timeout:
      end_time = time.time() + timeout
    self.event.clear()
    while (timeout is None) or (time.time() < end_time):
      self.event.wait(timeout)  # TODO: adjust timeout
      if (self.state == value):
        return value
    return None


  def _HandleReportDigitalInStatus(self, level):
    Debug('ReportDigitalInStatus digital_in %r %r' % (self.pin, level))
    self.state = level
    self.event.set()

  def _HandleSetChangeNotify(self, level):
    Info('SetChangeNotify %r %r' % (self.pin, level))
    self.notify = level         # this is an echo of what we sent
