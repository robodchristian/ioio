# Copyright 2012 Google Inc. All rights reserved

"""The low level protocol with the IOIO."""

import sys, time
import threading

import exception
import pyIO
import digital_in
#import uart

import ezlog
Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error

#TODO: some way to sync constants and sizes with C and Java

def TwoBytes(val):
  """Turn val into a 2 byte string."""
  return chr(val & 0xff) + chr((val >> 8) & 0xff)

def ThreeBytes(val):
  """Turn val into a 3 byte string."""
  return chr(val & 0xff) + chr((val >> 8) & 0xff) + chr((val >> 16) & 0xff)

class ProtoV1(threading.Thread):
  """Interface to and IOIO object (currently only over BlueTooth)."""
  # Message identifier constants from IOIOProtocol.java
  HARD_RESET                          = 0x00
  ESTABLISH_CONNECTION                = 0x00
  SOFT_RESET                          = 0x01
  CHECK_INTERFACE                     = 0x02
  CHECK_INTERFACE_RESPONSE            = 0x02
  SET_PIN_DIGITAL_OUT                 = 0x03
  SET_DIGITAL_OUT_LEVEL               = 0x04
  REPORT_DIGITAL_IN_STATUS            = 0x04
  SET_PIN_DIGITAL_IN                  = 0x05
  REPORT_PERIODIC_DIGITAL_IN_STATUS   = 0x05
  SET_CHANGE_NOTIFY                   = 0x06
  REGISTER_PERIODIC_DIGITAL_SAMPLING  = 0x07
  SET_PIN_PWM                         = 0x08
  SET_PWM_DUTY_CYCLE                  = 0x09
  SET_PWM_PERIOD                      = 0x0A
  SET_PIN_ANALOG_IN                   = 0x0B
  REPORT_ANALOG_IN_STATUS             = 0x0B
  SET_ANALOG_IN_SAMPLING              = 0x0C
  REPORT_ANALOG_IN_FORMAT             = 0x0C
  UART_CONFIG                         = 0x0D
  UART_STATUS                         = 0x0D
  UART_DATA                           = 0x0E
  SET_PIN_UART                        = 0x0F
  UART_REPORT_TX_STATUS               = 0x0F
  SPI_CONFIGURE_MASTER                = 0x10
  SPI_STATUS                          = 0x10
  SPI_MASTER_REQUEST                  = 0x11
  SPI_DATA                            = 0x11
  SET_PIN_SPI                         = 0x12
  SPI_REPORT_TX_STATUS                = 0x12
  I2C_CONFIGURE_MASTER                = 0x13
  I2C_STATUS                          = 0x13
  I2C_WRITE_READ                      = 0x14
  I2C_RESULT                          = 0x14
  I2C_REPORT_TX_STATUS                = 0x15
  ICSP_SIX                            = 0x16
  ICSP_REPORT_RX_STATUS               = 0x16
  ICSP_REGOUT                         = 0x17
  ICSP_RESULT                         = 0x17
  ICSP_PROG_ENTER                     = 0x18
  ICSP_PROG_EXIT                      = 0x19
  ICSP_CONFIG                         = 0x1A
  INCAP_CONFIGURE                     = 0x1B
  INCAP_STATUS                        = 0x1B
  SET_PIN_INCAP                       = 0x1C
  INCAP_REPORT                        = 0x1C
  SOFT_CLOSE                          = 0x1D

  # not yet connected, connected, incompatible firmware, disconnected
  INIT, CONNECTED, INCOMPATIBLE, DEAD = range(4) # connection state names

  # Pin use names (TODO: remove this and use pin_tracking)
  AVAILABLE, AIN, PWM, INCAP, UART, SPI, TWI, DIN, DOUT = range(9)

  def __init__(self, conn, establish_cb, reset_cb):
    """Create IOIO communication object.
    Do not reuse after Connect() succeeds.  Create a new object if needed.
    """
    self.conn = conn            # low level connection
    self.establish_cb = establish_cb # callback for connection establishment
    self.reset_cb = reset_cb         # callback for connection reset
    self._running = True        # flag for thread
    self.state = self.INIT      # connection state

    self.handler_table = {} # table of callbacks {NAME : { num : [handlers] }}

    threading.Thread.__init__(self)
    self.name = 'IOIO listener'
    self.setDaemon(1)           # terminate threads automatically on exit

  def Connect(self, timeout=3): # timeout in seconds
    """Connect to service previously found."""
    self.start()                # start listener thread (run())
    # wait for connect handshake
    delay = 0.01
    timeout = int(timeout / delay)
    count = 0
    while self.state == self.INIT:
      if not self.conn.CheckState():
        msg = "No connection transport"
        Error(msg)
        raise exception.IOException, msg

      time.sleep(delay)
      count += 1
      if count >= timeout:
        break
      if count > 50:            # attempt to wake it up
        self._SoftReset()
      if count > 100:           # kick it harder
        self._HardReset()
    if count:
      Info("Got handshake after %.3f" % (count * delay))

  def Disconnect(self):
    """Disconnect socket connection.
    The object should not be used after this.  Create a new one if needed.
    """
    if self.state == self.CONNECTED:
      self.SoftClose()

  def IsConnected(self):
    """Return True if currently connected, else False."""
    return self.state == self.CONNECTED

  def _Read(self, max_len=1024):
    """Read raw data from connection (up to max_len)."""
    data = ''
    count = 0
    while count < 50:           # re-try up to 0.5sec
      chunk = self.conn._Read(max_len-len(data))
      data += chunk
      if len(data) >= max_len:
        break
      time.sleep(0.01)
      count += 1
    if len(data) < max_len:
      msg = "Read returned %d instead of %d" % (len(data), max_len)
      Error(msg)
      raise IOError, msg
    return data

  def _Send(self, data):
    """Send raw data over connection."""
    #Debug("Sending: %s" % repr(map(ord, data)))
    try:
      data = self.conn._Send(data)
    except AttributeError:
      msg = "Write failed (lost connection)"
      Error(msg)
      raise IOError, msg

  # Batch control
  def BeginBatch(self):
    """Start batching (fixme)."""
    pass

  def EndBatch(self):
    """Finish batching (fixme)."""
    pass

  def _RegisterHandler(self, name, num, callback):
    """Setup a handler to a device object."""
    if not name in self.handler_table:
      self.handler_table[name] = {}
    hlist = self.handler_table[name]
    if not num in hlist:
      hlist[num] = list()
    hlist[num].append(callback)

  def _UnregisterHandler(self, name, num, callback):
    """Remove handler callbacks from table."""
    if not name in self.handler_table:
      Info("UnregisterHandler name isn't in table: %s" % name)
      return
    hlist = self.handler_table[name]
    if not num in hlist:
      Info("UnregisterHandler number isn't in %s entry: %s" % (name, num))
      return
    tlist = hlist[num]
    try:
      del tlist[hlist[num].index(callback)]
    except ValueError:
      pass

  def _CallHandlers(self, name, num, *args):
    """Call all handlers for name and num."""
    if not name in self.handler_table:
      Warn("_CallHandlers: invalid name %r" % name)
      return
    hlist = self.handler_table[name]
    if not num in hlist:
      Warn("_CallHandlers: invalid num %r for name %r" % (num, name))
      return
    for hh in hlist[num]:
      hh(*args)

  def CheckState(self):
    """If not in a connected state, raise an exception"""
    # typical turn around is 10-30ms
    if not self.conn or not self.conn.CheckState():
      msg = "No connection transport"
      Error(msg)
      raise exception.IOException, msg

    if self.state != self.CONNECTED:
      if self.state == self.DEAD:
        msg = "Connection was lost"
        Warn(msg)
        raise exception.ConnectionLostException, msg
      else:
        msg = "Never connected or invalid version"
        Warn(msg)
        raise exception.IllegalStateException, msg

  # General commands to IOIO
  def HardReset(self):
    """Reset board back to the bootloader."""
    self.CheckState()
    self._HardReset()

  def _HardReset(self):
    self._Send(chr(self.HARD_RESET) + 'IOIO')

  def SoftReset(self):
    """Reset all configuration to startup state."""
    self.CheckState()
    self._SoftReset()

  def _SoftReset(self):
    self._Send(chr(self.SOFT_RESET))

  def SoftClose(self):
    """."""
    self.CheckState()
    self._Send(chr(self.SOFT_CLOSE))

  def _SetPinDigitalOut(self, pin, mode, value):
    """Low level Tell IOIO to make pin an output."""
    if pin == 'LED':
      pin = 0
    value = 2 if value > 0 else 0               # turn into a bit field
    mode = mode & 1
    self._Send(chr(self.SET_PIN_DIGITAL_OUT) + chr(pin << 2 | value | mode))
    return pin

  def _SetDigitalOutLevel(self, pin, level):
    """Low level Set level of a digital out pin."""
    if pin == 'LED':
      pin = 0
    level = 1 if level > 0 else 0               # turn into a bit field
    self._Send(chr(self.SET_DIGITAL_OUT_LEVEL) + chr(pin << 2 | level))
    return pin

  def _SetPinDigitalIn(self, pin, mode):
    """Tell IOIO to make pin an input."""
    if pin == 'LED':
      pin = 0
    if mode == digital_in.MODE_PULL_UP:
      mode = 1
    elif mode == digital_in.MODE_PULL_DOWN:
      mode = 2
    else:
      mode = 0
    Debug("_SetPinDigitalIn %d %d" % (pin, mode))
    self._Send(chr(self.SET_PIN_DIGITAL_IN) + chr(pin << 2 | mode))
    return pin

  def _SetChangeNotify(self, pin, enable):
    """Tell IOIO to notify on pin change."""
    if pin == 'LED':
      pin = 0
    enable = 1 if enable else 0
    Debug("_SetChangeNotify %d %d" % (pin, enable))
    self._Send(chr(self.SET_CHANGE_NOTIFY) + chr(pin << 2 | enable))
    return pin

  def _UartConfigure(self, num, rate, speed4x, stop_bits, parity, flow_mode):
    """Configure UART."""
    if (num < 0) or (num >= 4):
      return None
    speed4x = 0x08 if speed4x else 0
    stop_bits = 0x04 if stop_bits else 0
    parity = 0x01 if parity else 0
    flow_mode = (flow_mode & 0x3) << 4
    conf = num << 6 | flow_mode | speed4x | stop_bits | parity
    print "UartConfig, conf=0x%x" % conf # DEBUG
    self._Send(chr(self.UART_CONFIG) + chr(conf) + TwoBytes(rate))
    return num

  def _UartClose(self, num):
    """Disable UART."""
    if (num < 0) or (num >= 4):
      return None
    self._Send(chr(self.UART_CONFIG) + chr(num << 6) + TwoBytes(0))
    return num

  def _SetPinUart(self, pin, num, tx, flow, enable):
    """Configure UART."""
    if (num < 0) or (num >= 4):
      return None
    enable = 0x80 if enable else 0
    tx = 0x40 if tx else 0
    flow = 0x20 if flow else 0
    # if flow && tx: set RTS.  if flow && !tx: set CTS
    self._Send(chr(self.SET_PIN_UART) + chr(pin) + chr(enable | tx | flow | num))
    return num

  def _UartData(self, num, data):
    """Send one data packet to uart."""
    if (num < 0) or (num >= 4):
      return None
    if len(data) > 64:
      return None
    # TODO: a bytearray would be faster here
    msg = chr(self.UART_DATA) + chr(len(data) - 1)
    msg += ''.join(data)        # turn array into string
    Debug("_UartData out %02x %d: '%s'" % (ord(msg[0]), ord(msg[1]), pyIO.ConditionallyEncode(msg[2:])))
    self._Send(msg)

  def _HandleSoftReset(self):
    Info('SoftReset')
    #self.handler_table = {}     # needed?  Object should un-register

  def _HandleAnalogPinStatus(self, pin, added):
    Info('AnalogPinStatus %r %r' % (pin, added))

  def _HandleReportAnalogInStatus(self, analog_frame_pins, values):
    Info('ReportAnalogInStatus %r %r' % (analog_frame_pins, values))

  def _HandleSpiData(self, spi_num, ssPin, data, size):
    Info('SpiData %r %r %r %r' % (spi_num, ssPin, data, size))

  def _HandleSpiReportTxStatus(self, spi_num, bytes_remaining):
    Info('SpiReportTxStatus %r %r' % (spi_num, bytes_remaining))

  def _HandleSpiOpen(self, spi_num):
    Info('SpiOpen %r' % spi_num)

  def _HandleSpiClose(self, spi_num):
    Info('SpiClose %r' % spi_num)

  def _HandleI2cOpen(self, i2c_num):
    Info('I2cOpen %r' % i2c_num)

  def _HandleI2cClose(self, i2c_num):
    Info('I2cClose %r' % i2c_num)

  def _HandleI2cResult(self, i2c_num, size, data):
    Info('I2cResult %r %r %r' % (i2c_num, size, data))

  def _HandleI2cReportTxStatus(self, i2c_num, bytes_remaining):
    Info('I2cReportTxStatus %r %r' % (i2c_num, bytes_remaining))

  def _HandleCheckInterfaceResponse(self, supported):
    Info('CheckInterfaceResponse %r' % supported)

  def _HandleIcspReportRxStatus(self, bytes_remaining):
    Info('IcspReportRxStatus %r' % bytes_remaining)

  def _HandleIcspResult(self, size, data):
    Info('IcspResult %r %r' % (size, data))

  def _HandleIcspOpen(self):
    Info('IcspOpen')

  def _HandleIcspClose(self):
    Info('IcspClose')

  def _HandleIncapOpen(self, incap_num):
    Info('IncapOpen %r' % incap_num)

  def _HandleIncapClose(self, incap_num):
    Info('IncapClose %r' % incap_num)

  def _HandleIncapReport(self, incap_num, size, data):
    Info('IncapReport %r %r %r' % (incap_num, size, data))

  def _FindDelta(self, newFormat):
    pass

  def run(self):
    """Listener thread.  Read bytes from connection and unpack"""
    # This is a direct port of IncomingHandler in IOIOProtocol.java
    try:
      while self._running:
        arg1 = ord(self._Read(1))
        if arg1 == self.ESTABLISH_CONNECTION:
          if (self._Read(1) != 'I' or self._Read(1) != 'O'
              or self._Read(1) != 'I' or self._Read(1) != 'O'):
            msg = "Bad establish connection magic"
            Error(msg)
            raise exception.IOException, msg
          hardware_id = self._Read(8)
          bootloader_id = self._Read(8)
          firmware_id = self._Read(8)
          if self.establish_cb(hardware_id, bootloader_id, firmware_id):
            self.state = self.CONNECTED
          else:
            self.state = self.INCOMPATIBLE

        elif arg1 == self.SOFT_RESET:
          self._HandleSoftReset()
          self.reset_cb()

        elif arg1 == self.REPORT_DIGITAL_IN_STATUS:
          arg1 = ord(self._Read(1))
          self._CallHandlers('HandleReportDigitalInStatus', arg1 >> 2, (arg1 & 0x01) == 1)

        elif arg1 == self.SET_CHANGE_NOTIFY:
          arg1 = ord(self._Read(1))
          self._CallHandlers('HandleSetChangeNotify', arg1 >> 2, (arg1 & 0x01) == 1)

        elif arg1 == self.REGISTER_PERIODIC_DIGITAL_SAMPLING:
          Warn("REPORT_PERIODIC_DIGITAL_SAMPLING not implemented")
          pass #TODO: implement

        elif arg1 == self.REPORT_PERIODIC_DIGITAL_IN_STATUS:
          Warn("REPORT_PERIODIC_DIGITAL_IN_STATUS not implemented")
          pass #TODO: implement

        elif arg1 == self.REPORT_ANALOG_IN_FORMAT:
          numPins = ord(self._Read(1))
          newFormat = []
          for i in range(numPins):
             newFormat[i] = ord(self._Read(1))

          addedPins, removedPins = self._FindDelta(newFormat)
          for i in removedPins:
              self._CallHandlers('HandleAnalogPinStatus', i, False)
          for i in addedPins:
            self._CallHandlers('HandleAnalogPinStatus', i, True)
          self.analog_frame_pins = newFormat

        elif arg1 == self.REPORT_ANALOG_IN_STATUS:
          # FIX! not reading right number of bytes.  Need to track analog_frame_pins
          # numPins = self.analog_frame_pins.length
          # values = []
          # for i in range(numPins):
          #   if (i % 4 == 0):
          #       header = ord(self._Read(1))
          #   values[i] = (ord(self._Read(1)) << 2) | (header & 0x03)
          #   header >>= 2
          # self._CallHandlers('HandleReportAnalogInStatus', analog_frame_pins, values)
          pass

        elif arg1 == self.UART_REPORT_TX_STATUS:
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          self._CallHandlers('HandleUartReportTxStatus', arg1 & 0x03, (arg1 >> 2) | (arg2 << 6))

        elif arg1 == self.UART_DATA:
          arg1 = ord(self._Read(1))
          sz = (arg1 & 0x3F) + 1
          data = self._Read(sz)
          self._CallHandlers('HandleUartData', arg1 >> 6, data)

        elif arg1 == self.UART_STATUS:
          arg1 = ord(self._Read(1))
          if ((arg1 & 0x80) != 0):
            self._CallHandlers('HandleUartOpen', arg1 & 0x03)
          else:
            self._CallHandlers('HandleUartClose', arg1 & 0x03)

        elif arg1 == self.SPI_DATA:
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          for i in range((arg1 & 0x3F) + 1):
            data[i] = ord(self._Read(1))
          self._CallHandlers('HandleSpiData', arg1 >> 6, arg2 & 0x3F, data, (arg1 & 0x3F) + 1)

        elif arg1 == self.SPI_REPORT_TX_STATUS:
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          self._CallHandlers('HandleSpiReportTxStatus', arg1 & 0x03, (arg1 >> 2) | (arg2 << 6))

        elif arg1 == self.SPI_STATUS:
          arg1 = ord(self._Read(1))
          if ((arg1 & 0x80) != 0):
            self._CallHandlers('HandleSpiOpen', arg1 & 0x03)
          else:
            self._CallHandlers('HandleSpiClose', arg1 & 0x03)

        elif arg1 == self.I2C_STATUS:
          arg1 = ord(self._Read(1))
          if ((arg1 & 0x80) != 0):
            self._CallHandlers('HandleI2cOpen', arg1 & 0x03)
          else:
            self._CallHandlers('HandleI2cClose', arg1 & 0x03)

        elif arg1 == self.I2C_RESULT:
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          if (arg2 != 0xFF):
            for i in range(arg2):
              data[i] = ord(self._Read(1))
          self._CallHandlers('HandleI2cResult', arg1 & 0x03, arg2, data)

        elif arg1 == self.I2C_REPORT_TX_STATUS:
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          self._CallHandlers('HandleI2cReportTxStatus', arg1 & 0x03, (arg1 >> 2) | (arg2 << 6))

        elif arg1 == self.CHECK_INTERFACE_RESPONSE:
          arg1 = ord(self._Read(1))
          self._CallHandlers('HandleCheckInterfaceResponse', (arg1 & 0x01) == 1)

        elif arg1 == self.ICSP_REPORT_RX_STATUS: # unsupported in this port
          arg1 = ord(self._Read(1))
          arg2 = ord(self._Read(1))
          self._CallHandlers('HandleIcspReportRxStatus', arg1 | (arg2 << 8))

        elif arg1 == self.ICSP_RESULT: # unsupported in this port
          data[0] = ord(self._Read(1))
          data[1] = ord(self._Read(1))
          self._CallHandlers('HandleIcspResult', 2, data)

        elif arg1 == self.ICSP_CONFIG: # unsupported in this port
          arg1 = ord(self._Read(1))
          if ((arg1 & 0x01) == 1):
            self._CallHandlers('HandleIcspOpen', None)
          else:
            self._CallHandlers('HandleIcspClose', None)

        elif arg1 == self.INCAP_STATUS:
          arg1 = ord(self._Read(1))
          if ((arg1 & 0x80) != 0):
            self._CallHandlers('HandleIncapOpen', arg1 & 0x0F)
          else:
            self._CallHandlers('HandleIncapClose', arg1 & 0x0F)

        elif arg1 == self.INCAP_REPORT:
          arg1 = ord(self._Read(1))
          size = arg1 >> 6
          if (size == 0):
            size = 4
          data = self._Read(size)
          self._CallHandlers('HandleIncapReport', arg1 & 0x0F, size, data)

        elif arg1 == self.SOFT_CLOSE:
          Info("Received soft close.")
          self._running = False # cause thread to exit
          self.state = self.DEAD
          self._HandleSoftReset() # close down all sub-objects

        else:
          Error("Protocol error.  Closing connection.")
          self.conn.Disconnect()
          self._running = False # cause thread to exit
          self.state = self.DEAD
          # BUG: This is a thread.  Who can catch this?
          msg = "Received unexpected command: 0x%x" % arg1
          Error(msg)
          raise exception.IOException, msg

    except IOError:
      Error("IO error.  Closing connection.")
      self.conn.Disconnect()
      # and exit thread
