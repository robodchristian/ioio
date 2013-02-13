#!/usr/bin/env python
"""Simple test case with no jumpers required."""

import os
import StringIO
import sys
import unittest
try:
  import exception
  import pyIO
  import ezlog
  import digital_in
  #import digital_out
  import uart
except ImportError:
  print "Unable to load pyIO."
  print "Try: PYTHONPATH=. IOIO='00:1F:81:00:08:30' tests/simple_test.py"
  sys.exit(1)

# Note: bluetooth address must be passed in throught IOIO
class SimpleTests(unittest.TestCase):
  # Handy (partial) list of PPSO pins
  ppso = (3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 27, 28, 29, 30, 31, 32)
  baud_table = (38400, 57600, 115200, 230400)

  def setUp(self):
    ezlog.LogFile(None)         # log to stderr until connected
    self.log = StringIO.StringIO()
    ezlog.LogLevel(ezlog.WARN)
    #ezlog.LogLevel(ezlog.INFO)
    #ezlog.LogLevel(ezlog.DEBUG)
    self.conn = pyIO.IOIO()
    addr = os.getenv('IOIO')
    #print "Waiting for connection...", self.id()   # DEBUG
    self.conn.WaitForConnect(addr) # takes a second or more
    #print "Connected"              # DEBUG
    ezlog.LogFile(self.log)

  def tearDown(self):
    ezlog.LogFile(None)
    self.conn.Disconnect()
    self.conn.WaitForDisconnect()
    self.conn = None            # free object

  def testOpen(self):
    """Simple test of opening various devices."""
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    self.conn.BeginBatch()
    led.Write(0)
    self.conn.EndBatch()

    in1 = self.conn.OpenDigitalInput(16)
    self.assertTrue(in1 != None,
                    "Expected digital_in object.  log=\n%s" % self.log.getvalue())
    _ = in1.Read()              # value is undefined

    self.assertRaises(exception.IllegalArgumentException, self.conn.OpenDigitalInput, 16) # duplicate pin

    in2 = self.conn.OpenDigitalInput(17, digital_in.MODE_PULL_UP)
    self.assertTrue(in2 != None,
                    "Expected digital_in object.  log=\n%s" % self.log.getvalue())
    data = in2.Read()              # should be high
    self.assertTrue(data,
                    "Expected True reading.  log=\n%s" % self.log.getvalue())

    in3 = self.conn.OpenDigitalInput(18, digital_in.MODE_PULL_DOWN)
    self.assertTrue(in3 != None,
                    "Expected digital_in object.  log=\n%s" % self.log.getvalue())
    data = in3.Read()              # value is undefined
    self.assertFalse(
        data, "Expected False reading.  log=\n%s" % self.log.getvalue())


    self.assertRaises(exception.IllegalArgumentException, self.conn.OpenUart, 22, 23, 19200) # invalid pins for uart

    for ii in range(4):         # standard IOIO has 4 uarts
      uobj = self.conn.OpenUart(self.ppso[ii*2], self.ppso[ii*2+1], self.baud_table[ii])
      self.assertTrue(uobj != None,
                    "Expected uart object %d.  log=\n%s" % (
                        ii, self.log.getvalue()))
      data = uobj.read()         # should immediately return nothing
      self.assertFalse(data,
                    "Expected no data %d.  log=\n%s" % (
                        ii, self.log.getvalue()))

    self.assertRaises(exception.IllegalArgumentException, self.conn.OpenUart, 47, 48, 19200) # out of uarts

    led.Write(1)
    # Make sure close works
    led.Close()
    in1.Close()
    uobj.Close()
    self.conn.Disconnect()
    self.conn.WaitForDisconnect()
    self.assertRaises(exception.ConnectionLostException, led.Write, 0)
    # the rest will close on exit
    print 'Test OK.  Final log:\n%s' % self.log.getvalue()   # DEBUG

  def testFlow(self):
    """Test Uart flow control modes."""
    modes = ({'flow' : uart.FLOW_NONE},
             {'flow' : uart.FLOW_IRDA},
             {'flow' : uart.FLOW_RTSCTS, 'rts_pin' : 29, 'cts_pin' : 30},
             {'flow' : uart.FLOW_RS485, 'rts_pin' : 31, 'cts_pin' : 32},
             )
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    led.Write(0)

    for ii in range(4):
      kwargs = modes[ii]
      print "Requesting uart object %r" % kwargs # DEBUG
      uobj = self.conn.OpenUart(self.ppso[ii*2], self.ppso[ii*2+1], 38400, **kwargs)
      self.assertTrue(uobj != None,
                      "Expected uart object %r.  log=\n%s" % (
                        kwargs, self.log.getvalue()))
    led.Write(1)
    print "Flow done"


if __name__ == "__main__":
    unittest.main()
