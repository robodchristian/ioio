#!/usr/bin/python
# Copyright 2012 Google Inc. All rights reserved

"""Top level interface to an IOIO.

This is written for a PC to talk to an IOIO (no Android requirement),
but it could theoretically work with the Python scripting environment
under Android (not tested).

PyBluez does the connection and is currently limited to Linux and
WinXP support.

Communication from the IOIO is handled in a thread.
"""

from bluetooth import *
import difflib
import time

import connect_bt
import exception
import protov1
import pin_tracking

import digital_in
import digital_out
import uart

import ezlog
Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error

LED_PIN = 'LED'                 # Use this for the LED
INVALID_PIN = -1                # Use this if pin isn't needed (e.g. Uart)

# App versions that we know we can talk to
# Note: only 0326 has been tested, but the others should work
_SUPPORTED_VERSIONS = ('IOIO0311', 'IOIO0323', 'IOIO0324', 'IOIO0326')

# shell compatible syntax allows version to be extracted by Makefile
VERSION="pyIO0002"

#TODO: be able to connect of USB (IOIO-OTG)

class IOIO(object):
  """Interface to and IOIO object (currently only over BlueTooth)."""

  def __init__(self):
    """Create IOIO communication object.
    Do not reuse after Connect() succeeds.  Create a new object if needed.
    """

    self.pins = None            # tracks pin capability and use
    self.objects = []           # list of sub-objects

    self.hardware_id = None      # hardware version
    self.bootloader_id = None    # bootload version
    self.firmware_id = None      # firmware version
    self.ioiolib_id = VERSION    # This interface library version

    self.conn = connect_bt.BluetoothConnection()
    # TODO: start with a generic protocol, then select specific
    self.proto = protov1.ProtoV1(
        self.conn, self._HandleEstablishConnection, self._HandleSoftReset)

  def WaitForConnect(self,
                     addr=None): # Address to connect to.  BUG: only applies to BT
    """Find a connection to an IOIO via Bluetooth (or eventually USB)."""
    # TODO: poll or start threads checking both BlueTooth and USB
    if not self.conn:
      msg = "No connection transport"
      Error(msg)
      raise exception.IOException, msg

    while True:
      info = self.conn.Find(addr)
      if info:
        self.conn.Connect()
        print self.conn         # DEBUG
        self.proto.Connect()
        return

  def Disconnect(self):
    """Disconnect socket connection.
    The object should not be used after this.  Create a new one if needed.
    """
    self.proto.Disconnect()     # which sends a SoftClose

  def WaitForDisconnect(self, timeout=2):
    """Wait for Disconnect() to finish."""
    count = timeout * 10
    while self.proto.state != self.proto.DEAD:
      count -= 1
      if count <= 0:
        break
      time.sleep(0.1)

  # General commands to IOIO
  def SoftReset(self):
    """Reset all configuration to startup state.
    All pin objects must be closed."""
    self.proto.SoftReset()

  def HardReset(self):
    """Reset board back to the bootloader (for re-programming)."""
    self.proto.HardReset()

  def GetVersions(self):
    """return (hardware, bootloader, app, pyIOlib)"""
    return (self.hardware_id, self.bootloader_id, self.firmware_id, self.ioiolib_id)

  # Batch control
  def BeginBatch(self):
    """Start batching (fixme)."""
    self.proto.BeginBatch()

  def EndBatch(self):
    """Finish batching (fixme)."""
    self.proto.EndBatch()

  # Open pin commands
  def OpenDigitalOutput(self, pin, mode=digital_out.MODE_NORMAL, start_value=0):
    """Configure a pin as a digital out and return object."""
    self.proto.CheckState()
    if ((mode < digital_out.MODE_NORMAL)
        or (mode > digital_out.MODE_OPEN_DRAIN)):
      msg = "Invalid mode %s for pin %r" % (mode, pin)
      Error(msg)
      raise exception.IllegalArgumentException, msg
    self.pins.AllocatePin(pin, self.pins.DOUT)
    try:
      obj = digital_out.DigitalOutput(self, pin, mode, start_value)
      self.objects.append(obj)
      return obj
    except exception.IllegalArgumentException:
      self.pins.FreePin(pin)
      raise

  def OpenDigitalInput(self, pin, mode=digital_in.MODE_FLOATING):
    """Configure a pin as a digital out and return object."""
    self.proto.CheckState()
    if ((mode < digital_in.MODE_FLOATING)
        or (mode > digital_in.MODE_PULL_DOWN)):
      msg = "Invalid mode %s for pin %r" % (mode, pin)
      Error(msg)
      raise exception.IllegalArgumentException, msg
    self.pins.AllocatePin(pin, self.pins.DIN)
    try:
      obj = digital_in.DigitalInput(self, pin, mode)
      self.objects.append(obj)
      return obj
    except exception.IllegalArgumentException:
      self.pins.FreePin(pin)
      raise

  def OpenUart(self, rx_pin, tx_pin, baud, parity=uart.PARITY_NONE, stop_bits=uart.STOP_BITS_ONE,
               flow=uart.FLOW_NONE, rts_pin=-1, cts_pin=-1):
    """Open an UART."""
    # BUG: we require RX and CTS to support both in or out, even though input only would allow more pins
    if (baud <= 0):
      msg = "Baud must be > 0"
      Error(msg)
      raise exception.IllegalArgumentException, msg
    if (rx_pin <= 0) and (tx_pin <= 0):
      msg = "At least a receive or transmit pin must be specified"
      Error(msg)
      raise exception.IllegalArgumentException, msg
    if (flow >= uart.FLOW_RTSCTS) and ((rts_pin < 0) or (cts_pin < 0)):
      msg = "Both RTS and CTS must be set for flow control"
      Error(msg)
      raise exception.IllegalArgumentException, msg
    self.proto.CheckState()

    pins = []                   # track allocated pins in case we abort
    num = None
    try:
      if (flow >= uart.FLOW_RTSCTS) and (rts_pin > 0):
        self.pins.AllocatePin(rts_pin, self.pins.UART)
        pins.append(rts_pin)
      if (flow >= uart.FLOW_RTSCTS) and (cts_pin > 0):
        self.pins.AllocatePin(cts_pin, self.pins.UART)
        pins.append(cts_pin)
      if (rx_pin > 0):
        self.pins.AllocatePin(rx_pin, self.pins.UART)
        pins.append(rx_pin)
      if (tx_pin > 0):
        self.pins.AllocatePin(tx_pin, self.pins.UART)
        pins.append(tx_pin)
      num = self.pins.AllocateFunction(self.pins.UART)
      obj = uart.Uart(self, num, rx_pin, tx_pin, baud, parity, stop_bits, flow, rts_pin, cts_pin)
      self.objects.append(obj)
      return obj
    except exception.IllegalArgumentException:
      if num is not None:
        self.pins.FreeFunction(self.pins.UART, num)
      for pp in pins:
        self.pins.FreePin(pp)
      raise

  # These pin types have not been implemented yet.
  def OpenAnalogInput(self, pin):
    return None

  def OpenPwmOutput(self, pin, freqHz):
    return None

  def OpenTwiMaster(self, twi_num, rate, smbus):
    return None

  def OpenSpiMaster(self, miso, mosi, clk, slave_select, rate, config):
    return None

  def OpenPulseInput(self, spec, rate, mode, doublePrecision):
    return None


  def _ForgetSub(self, sub):
    """Remove sub-object from our list."""
    try:
      del self.objects[self.objects.index(sub)]
    except ValueError:
      pass

  def _HandleEstablishConnection(self, hardware_id, bootloader_id, firmware_id):
    """Callback when IOIO first establishes the connection."""
    self.hardware_id = hardware_id
    self.bootloader_id = bootloader_id
    self.firmware_id = firmware_id
    Warn('EstablishConnection: %s %s %s' % (hardware_id, bootloader_id, firmware_id))
    # TODO: better check of compatibility with firmware_id
    if not self.firmware_id in _SUPPORTED_VERSIONS:
      msg = "Error: untested firmware version: %s" % self.firmware_id
      Error(msg)
      raise exception.IncompatibilityException, msg
    self.pins = pin_tracking.PinTracker(hardware_id)
    self._HandleSoftReset()
    return True

  def _HandleSoftReset(self):
    """Callback when the connection is reset."""
    # Note: User code finds out that the connection was lost when
    # CheckState() raises exception.ConnectionLostException
    for oo in self.objects:     # close all sub-objects
      oo.Close()
    self.objects = []
    self.pins.Reset()


class BaseIOIOLooper(object):
  """Subclass this to create a handy application loop."""

  def Setup(self, ioio):
    """Called on connection creation with an ioio object."""
    self.ioio = ioio
    Info("Got connection to ioio %r" % ioio.GetVersions())

  def Loop(self):
    """Main application loop."""
    Info("Doing application bit...")
    time.sleep(2)

  def Incompatible(self):
    """Called if we connect to an incompatible IOIO."""
    Warn("Unsupported IOIO version: %r" % self.ioio.GetVersions())

  def Disconnected(self):
    """Called when the connection is lost."""
    Info("Connection closed")
    pass


def IOIOActivity(loop_runner, addr=None):
    """Helper function to connect and then execute loop_runner.

    loop_runner is a subclass object of BaseIOIOLooper.
    addr is a specific address to pass to WaitForConnection()
    """
    conn = IOIO()
    conn.WaitForConnect(addr)
    try:
      try:
        loop_runner.Setup(conn)

        while True:
          loop_runner.loop()

      except exception.IncompatibilityException:
        loop_runner.Incompatible()
        pass
      except (exception.IOException, exception.ConnectionLostException,
              exception.IllegalStateException, exception.IllegalArgumentException):
        pass
    finally:
      loop_runner.Disconnected()


# These are support utilities
def CheckAscii(string):
  """Return true if all characters are ascii."""
  for ss in string:
    if ((ss < ' ') or (ss > '~')):
      return False
  return True


def HexEncode(string):
  """Convert string into a hex code sequence."""
  out_string = ''               # byte array would be faster
  for ss in string:
    out_string += " %%%02x" % ord(ss)
  return out_string


def ConditionallyEncode(strings):
  """Given an array of string lines, convert lines with non-ascii to hex."""

  try:                          # test if we have an array of strings
    for nn in range(len(strings)):
      if CheckAscii(strings[nn]):
        continue
      strings[nn] = HexEncode(strings[nn])
    return strings
  except TypeError:
    if not CheckAscii(strings):
      strings = HexEncode(strings)
    return strings


def DiffBuffers(s1, s2, s1_name=None, s2_name=None):
  """Split strings into line and return line by line difference."""
  s1 = ConditionallyEncode(s1.splitlines())
  s2 = ConditionallyEncode(s2.splitlines())
  delta = difflib.context_diff(s1, s2, s1_name, s2_name)
  if delta:
    blob = ''
    for ln in delta:
      if blob:
        blob += '\n' + ln
      else:
        blob = ln
    return blob
  return ""
