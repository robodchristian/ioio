# Copyright 2012 Google Inc. All rights reserved

"""Universal asynchronous receiver transmitter (AKA serial port)
support for IOIO.
"""

import time, Queue

import exception
import pyIO
import ezlog

Debug  = ezlog.Debug
Info   = ezlog.Info
Warn   = ezlog.Warn
Error  = ezlog.Error


# Parity
PARITY_NONE, PARITY_EVEN, PARITY_ODD = range(3)
# Stop bits
STOP_BITS_ONE, STOP_BITS_TWO = range(2)
# Flow control modes
FLOW_NONE, FLOW_IRDA, FLOW_RTSCTS, FLOW_RS485 = range(4)

class Uart(object):
  """Universal asynchronous receiver transmitter (AKA serial port) object.
  """

  def __init__(self, ioio, num, rx_pin, tx_pin, baud, parity=PARITY_NONE, stop_bits=STOP_BITS_ONE,
               flow=FLOW_NONE, rts_pin=-1, cts_pin=-1):
    self.ioio = ioio               # top level interface
    self.num = num                        # UART number
    self.rx_pin = rx_pin                  # receive pin number
    self.tx_pin = tx_pin                  # transmit pin number
    self.flow = flow                      # flow control mode
    self.rts_pin = rts_pin                # Request To Send flow control output
    self.cts_pin = cts_pin                # Clear To Send flow control input
    self.parity = parity
    self.stop_bits = stop_bits
    self.in_queue = Queue.Queue()    # input from receive (variable length strings)
    self.in_buff = []                    # readahead buffer
    self.out_queue = Queue.Queue()   # output to transmit (variable length strings)
    self.out_buff = []                   # partial output buffer
    self.bytes_to_tx = 0                 # track buffer space free for data

    self.ioio.proto.CheckState()
    # register handlers
    self.ioio.proto._RegisterHandler('HandleUartReportTxStatus', self.num,
                                     self._HandleUartReportTxStatus)
    self.ioio.proto._RegisterHandler('HandleUartData', self.num,
                                     self._HandleUartData)
    self.ioio.proto._RegisterHandler('HandleUartOpen', self.num,
                                     self._HandleUartOpen)
    self.ioio.proto._RegisterHandler('HandleUartClose', self.num,
                                     self._HandleUartClose)
    # For compatibility, set RTS/CTS first.  TX/RX will override if not supported.
    if (self.flow >= FLOW_RTSCTS) and (self.rts_pin > 0):
      self.ioio.proto._SetPinUart(self.rts_pin, self.num, True, True, True)
    if (self.flow >= FLOW_RTSCTS) and (self.cts_pin > 0):
      self.ioio.proto._SetPinUart(self.cts_pin, self.num, False, True, True)
    if self.rx_pin > 0:
      self.ioio.proto._SetPinUart(self.rx_pin, self.num, False, False, True)
    if self.tx_pin > 0:
      self.ioio.proto._SetPinUart(self.tx_pin, self.num, True, False, True)
    speed4x = True
    rate = int(round(4000000.0 / baud) - 1);
    if (rate > 65535) or (self.flow == FLOW_IRDA):
      speed4x = False
      rate = int(round(1000000.0 / baud) - 1);
      true_baud = 1000000.0 / (rate + 1)
    else:
      true_baud = 4000000.0 / (rate + 1)
    # It isn't clear how much baud error is acceptable for a given UART type
    # At 10 bits per byte (8+start+stop), a 10% error will always be fatal.
    # Microchip UARTS sub-samples each bit 4x in 4x mode, or 16x in slow mode.
    if abs(true_baud - baud) >= (baud * 0.00625):
      error = 100 * abs(true_baud - baud) / baud
      Warn("Warning true baud %.1f != requested baud %.1f.  %.2f%% error" % (true_baud, baud, error))
    Info("baud %d -> 4x=%d div=%d" % (baud, speed4x, rate))
    Info("num %d rate %d speed4x %d stop %d parity %d flow %d" % (
        self.num, rate, speed4x, self.stop_bits, self.parity, self.flow))
    self.ioio.proto._UartConfigure(self.num, rate, speed4x, self.stop_bits, self.parity, self.flow);

  def __del__(self):
    """We need to break back references so garbage collection can work."""
    if not self.ioio:
      return
    if self.ioio.proto.IsConnected:
      self.ioio.proto._UartClose(self.num)
    # un-register handlers
    self.ioio.proto._UnregisterHandler('HandleUartReportTxStatus', self.num,
                                       self._HandleUartReportTxStatus)
    self.ioio.proto._UnregisterHandler('HandleUartData', self.num,
                                       self._HandleUartData)
    self.ioio.proto._UnregisterHandler('HandleUartOpen', self.num,
                                       self._HandleUartOpen)
    self.ioio.proto._UnregisterHandler('HandleUartClose', self.num,
                                       self._HandleUartClose)
    if (self.flow >= FLOW_RTSCTS) and (self.rts_pin > 0):
      self.ioio.pins.FreePin(self.rts_pin)
    if (self.flow >= FLOW_RTSCTS) and (self.cts_pin > 0):
      self.ioio.pins.FreePin(self.cts_pin)
    self.ioio.pins.FreePin(self.rx_pin)
    self.ioio.pins.FreePin(self.tx_pin)
    self.ioio.pins.FreeFunction(self.ioio.pins.UART, self.num)
    self.ioio._ForgetSub(self)  # tell parent to forget about us
    self.ioio = None            # remove circular link

  def GetInputStream(self):
    """Object implements a standard file input stream with: read, readline, close.

    Note that there is no select() or poll() support
    """
    return self

  def GetOutputStream(self):
    """Object implements a standard file output stream with: write, writelines, close, flush, isatty

    Note that there is no select() or poll() support
    """
    return self

  def read(self, sz=-1, block=True, timeout=None):
    """Read bytes from buffer."""
    if sz <= 0:                 # Return whatever is waiting.  No blocking.
      if self.in_buff:
        ret_buff = self.in_buff
        self.in_buff = []
      else:
        ret_buff = []
      while True:
        try:
          chunk = self.in_queue.get(False)
          ret_buff += chunk
        except Queue.Empty:
          break
      ret_buff = ''.join(ret_buff)  # list to string
      Debug("read(%d) -> %r buff=%r" % (sz, ret_buff, self.in_buff))
      return ret_buff

    # Read a specific amount
    #Debug("read(%d) buff=%r" % (sz, self.in_buff))
    todo = sz
    if self.in_buff:
      rsz = min(len(self.in_buff), todo)
      ret_buff = self.in_buff[:rsz]
      del self.in_buff[:rsz]
      todo -= rsz
    else:
      ret_buff = []

    while todo > 0:
      chunk = self.in_queue.get(block, timeout) # Bug? inter-chunk timeout, not absolute
      #Debug("read todo=%d chunk=%r" % (todo, chunk))
      rsz = min(len(chunk), todo)
      if len(chunk) <= rsz:
        ret_buff += chunk
        todo -= len(chunk)
      elif len(chunk) > rsz:
        ret_buff += chunk[:todo]
        self.in_buff += chunk[todo:]
        todo = 0
    ret_buff = ''.join(ret_buff)  # list to string
    Debug("read(%d) -> %r buff=%r" % (sz, ret_buff, self.in_buff))
    return ret_buff
  Read = read                 # alternate naming style

  def close(self):              # close stream
    self.flush()
    self.__del__()
  Close = close                 # close object = close stream

  def isatty(self):
    return False

  def _OutputPending(self):
    return len(self.out_buff) > 0 or self.out_queue.qsize()

  def flush(self):
    """Wait until all output has been sent."""
    while self._OutputPending():
      Info("Waiting for output to drain %d + %d" % (len(self.out_buff), self.out_queue.qsize()))
      time.sleep(1.0)           # FIX: wait on event?

  def writelines(self, lines):
    """Write a iterable of strings.  No line termination is added."""
    for ll in lines:
      self.write(ll)

  def write(self, data):        # standard file naming conventions
    """Write data to file.  No newline conversions are done."""
    if not self.ioio:
      raise exception.ConnectionLostException
    else:
      self.ioio.proto.CheckState()
    self.out_queue.put(data)
    while self._OutputPending() and self.bytes_to_tx > 0:
      self._SendBytesToTx(self.bytes_to_tx)

  Write = write                 # alternate naming style

  def _HandleUartReportTxStatus(self, bytes_to_add):
    """Let us know how much buffer is available."""
    # This only triggers with the buffer crosses 50%
    Debug('UartReportTxStatus %r' % bytes_to_add)
    self.bytes_to_tx = bytes_to_add
    while self._OutputPending() and self.bytes_to_tx > 0:
      self._SendBytesToTx(self.bytes_to_tx)

  def _SendBytesToTx(self, bytes_to_add):
    todo = min(bytes_to_add, 64)
    if self.out_buff:
      rsz = min(len(self.out_buff), todo)
      ret_buff = self.out_buff[:rsz]
      del self.out_buff[:rsz]
      Debug("ret_buff=%d self.out_buff=%d" % (len(ret_buff), len(self.out_buff)))
      todo -= rsz
    else:
      ret_buff = []
    while todo > 0:
      try:
        chunk = self.out_queue.get(False)
      except Queue.Empty:
        break
      rsz = min(len(chunk), todo)
      if len(chunk) <= rsz:
        ret_buff += chunk
        todo -= len(chunk)
      elif len(chunk) > rsz:
        ret_buff += chunk[:todo]
        self.out_buff = list(chunk[todo:])
        todo = 0
    if ret_buff:
      #Debug('Sending %r' % ret_buff)
      self.ioio.proto._UartData(self.num, ret_buff)
      self.bytes_to_tx -= len(ret_buff)

  def _HandleUartData(self, data):
    Debug('UartData in on %d, %d: %s' % (self.num, len(data), pyIO.ConditionallyEncode(data)))
    self.in_queue.put(data)     # put entire chunk

  def _HandleUartOpen(self):
    Info('UartOpen %r' % self.num)
    # TODO: mark uart as allocated

  def _HandleUartClose(self):
    Info('UartClose %r' % self.num)
    # TODO: mark uart as free
