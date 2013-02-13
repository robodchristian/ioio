# Copyright 2012 Google Inc. All rights reserved

"""This file manages all the pins

Track what each pin can do (see also buildmap.py and pin_map.py), and
what pins and functions are currently allocated.
"""

import pin_map
import exception

import ezlog
Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error

# There can be alternate package IOIOs in the future. so track capabilities
# name -> (pin_table, AIN, PWM, INCAP, UART, SPI, TWI, DIN, DOUT)
_HARDWARE_MAP = {
    'SPRK0016' : (pin_map.PIN_FUNCTION, 16, 9, 9, 4, 3, 3, 48, 48),
    'SPRK0015' : (pin_map.PIN_FUNCTION, 16, 9, 9, 4, 3, 3, 48, 48),
    }

class PinTracker(object):
  """Track usage of IOIO pins."""

  # Pin use names (Note that these are also HARDWARE_MAP indexes)
  AVAILABLE, AIN, PWM, INCAP, UART, SPI, TWI, DIN, DOUT = range(9)

  # list of possible functions (handy for loops)
  FUNCTION_LIST = (AIN, PWM, INCAP, UART, SPI, TWI, DIN, DOUT)

  # Map our function definition to hardware capability indexes
  _MAP_FUNC_TO_HARDWARE = {     # { our_function_index : pin_map_index }
      AIN   : pin_map.A2D,
      PWM   : pin_map.PPSO,
      INCAP : pin_map.PPSI,
      UART  : pin_map.PPSO,     # BUG: needs 1 in + 1 out, be gets all IO pins
      SPI   : pin_map.PPSO,     # BUG: needs 1 in + 2/3 out, be gets all IO pins
      TWI   : pin_map.I2C,
      DIN   : None,             # None = Any
      DOUT  : None,             # None = Any
      }

  def __init__(self, hardware_id):
    """Pin tracker object.

    Track the usage mode for each pin on an IOIO
    """
    self.hardware_id = hardware_id
    if hardware_id in _HARDWARE_MAP:
      self.hardware_map = _HARDWARE_MAP[hardware_id] # function unit counts
      self.pin_map = self.hardware_map[0]
    else:
      Error("Hardware %r not in internal database" % hardware_id)
      self.pin_map = {}
    self.pin_mode = {}         # Current pin mode { pin_num: use }
    self.function_mode = {}    # Assigned function blocks { name : [assigned, ...] }
    for ff in self.FUNCTION_LIST:
      self.function_mode[ff] = {}
    self.Reset()

  def Reset(self):
    """Reset all pins to initial state."""
    for kk in self.pin_map:     # initialize pin mode table
      self.pin_mode[kk] = self.AVAILABLE
    for ff in self.FUNCTION_LIST:
      for ii in range(self.hardware_map[ff]): # count of function blocks
        self.function_mode[ff][ii] = self.AVAILABLE

  def IsValid(self, pin):
    """Return True if a valid pin (for this hardware)."""
    return pin in self.pin_mode

  def IsAvailable(self, pin):
    """Return True if pin is available."""
    return self.pin_mode[pin] == self.AVAILABLE

  def CanDo(self, pin, function):
    """See if pin can do function."""
    hwcap = self._MAP_FUNC_TO_HARDWARE[function]
    if (hwcap == None):         # None means ANY
      return True
    #print 'CanDo', pin, 'hwcap', hwcap, 'maps to', self.pin_map[pin] # DEBUG
    return self.pin_map[pin][hwcap]

  def AllocatePin(self, pin, function):
    """Mark a pin as in use."""
    if not self.IsValid(pin):
      msg = "Invalid pin %r" % pin
      Warn(msg)
      raise exception.IllegalArgumentException, msg

    if not self.IsAvailable(pin):
      msg = "Pin in use %r" % pin
      Warn(msg)
      raise exception.IllegalArgumentException, msg

    if not self.CanDo(pin, function):
      msg = "Pin %r cannot be used for requested function %r" % (pin, function)
      Warn(msg)
      raise exception.IllegalArgumentException, msg

    self.pin_mode[pin] = function

  def FreePin(self, pin):
    """Free a pin."""
    if pin not in self.pin_mode:
      Warn("Invalid pin %r" % pin)
      return None
    self.pin_mode[pin] = self.AVAILABLE
    return True

  def AllocateFunction(self, function):
    """Find a free instance of a given function."""
    func_mode = self.function_mode[function]
    for ii in range(self.hardware_map[function]):
      if func_mode[ii] == self.AVAILABLE:
        func_mode[ii] = function
        return ii
    msg = "No free function block of type %r" % function
    Warn(msg)
    raise exception.IllegalArgumentException, msg

  # TODO: call this on object destruction (BUG: no back reference)
  def FreeFunction(self, function, num):
    """Find a free instance of a given function."""
    func_mode = self.function_mode[function]
    if not num in func_mode:
      return False
    func_mode[num] = self.AVAILABLE
    return True

  def ListPins(self, function):
    """Return list of pins implementing a function."""
    plist = []
    func_mode = self.function_mode[function]
    for ii in range(self.hardware_map[function]):
      if func_mode[ii] != self.AVAILABLE:
        plist.append(ii)
    return plist
