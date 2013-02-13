#!/usr/bin/env python
"""For this test case, jumper 3-5, 6-7, 10-11, 12-13, 27-28 (all are PPSO).
Note that the programmer is using 35-36.  Error out is 4."""

import os
import StringIO
import sys
import time
import unittest

try:
    import pyIO
    import ezlog
    #import digital_in
    #import digital_out
    import uart
except ImportError:
    print "Unable to load pyIO."
    print "Try: PYTHONPATH=. IOIO='00:1F:81:00:08:30' tests/simple_test.py"
    sys.exit(1)

# This is long enough for multiple sends and flow control
_MSG = """The limerick packs laughs anatomical\r
In space that is quite economical.\r
But the good ones I've seen\r
So seldom are clean\r
And the clean ones so seldom are comical.\r
\r
        ~!@#$%^&*()_+[];',./-={}|:"<>?\r
\r
There was a young rustic named Mallory,\r
who drew but a very small salary.\r
When he went to the show,\r
his purse made him go\r
to a seat in the uppermost gallery.\r
\r
There was a Young Person of Smyrna\r
Whose grandmother threatened to burn her\r
But she seized on the cat,\r
and said 'Granny, burn that!\r
You incongruous old woman of Smyrna!'\r
"""

def ReadUntilDone(conn, eof_limit=3, delay=0.1):
  """Keep reading until getting nothing eof_limit times (after delay)."""
  readback = ''
  eof_count = 0
  while eof_count < eof_limit:
    chunk = conn.read()
    if not chunk:
      eof_count += 1
      time.sleep(delay)
      continue
    else:
      eof_count = 0
      readback += chunk
  return readback



# Note: bluetooth address must be passed in throught IOIO
class SimpleTests(unittest.TestCase):
  baud = 115200 #38400

  def setUp(self):
    ezlog.LogFile(None)         # log to stderr until connected
    self.log = StringIO.StringIO()
    ezlog.LogLevel(ezlog.WARN)
    ezlog.LogLevel(ezlog.INFO)
    #ezlog.LogLevel(ezlog.DEBUG)
    self.conn = pyIO.IOIO()
    addr = os.getenv('IOIO')
    self.conn.WaitForConnect(addr) # takes a second or more
    #DEBUG ezlog.LogFile(self.log)

  def tearDown(self):
    ezlog.LogFile(None)
    self.conn.Disconnect()
    self.conn.WaitForDisconnect()
    self.conn = None            # free object

  def testFlowLoop(self):
    """Test loopback of UART."""
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    led.Write(0)                # LED on
    count = 0
    for mode in (uart.FLOW_NONE, uart.FLOW_RTSCTS, uart.FLOW_RS485, uart.FLOW_IRDA):
      led.Write(count&1)                # LED on

      # Uart looped back to itself
      if mode < uart.FLOW_RTSCTS:
        uobj = self.conn.OpenUart(6, 7, self.baud, flow=mode)
      else:
        uobj = self.conn.OpenUart(6, 7, self.baud, flow=mode, rts_pin=27, cts_pin=28)
      self.assertTrue(uobj != None,
                      "Expected uart object.  log=\n%s" % self.log.getvalue())
      uobj.write(_MSG)
      readback = ReadUntilDone(uobj)
      if ((mode == uart.FLOW_IRDA) and (ord(readback[0]) == 0)):
        # We get an extra initial 0 on IRDA.  Just ignore it.
        readback = readback[1:]
      self.assertEqual(_MSG, readback, "mode: %d Read back %d != msg %d:\n%s" % (
          mode, len(readback), len(_MSG), pyIO.DiffBuffers(_MSG, readback, 'reference', 'readback')))
      uobj.Close()

    led.Write(1)                # LED off
    print 'Test OK.  Final log:\n%s' % self.log.getvalue()   # DEBUG

  def testFlowStopStart(self):
    """Test control of flow lines."""
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    led.Write(0)                # LED on

    out1 = self.conn.OpenDigitalOutput(27)
    self.assertTrue(out1 != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    out1.Write(1)                # flow disabled

    in1 = self.conn.OpenDigitalInput(12)
    self.assertTrue(led != None,
                    "Expected digital_in object.  log=\n%s" % self.log.getvalue())
    # Uart looped back to itself
    uobj = self.conn.OpenUart(6, 7, self.baud, flow=uart.FLOW_RTSCTS, rts_pin=13, cts_pin=28)
    self.assertTrue(uobj != None,
                    "Expected uart object.  log=\n%s" % self.log.getvalue())
    rts_state = in1.Read()
    self.assertTrue(rts_state, "Read in RTS not true: %r" % rts_state)

    #uobj.write(_MSG)
    uobj.write(_MSG[:100])
    readback = ReadUntilDone(uobj)
    self.assertEqual('', readback, "Read back %d != 0: %s" % (
        len(readback), self.log.getvalue()))

    out1.Write(0)                # flow enabled
    uobj.write(_MSG[100:])
    time.sleep(0.1)              # let serial data start flowing
    led.Write(1)                # LED off
    readback = ReadUntilDone(uobj)
    led.Write(0)                # LED on
    self.assertEqual(_MSG, readback, "Read back %d != msg %d.  Reference:\n%s\nRead:\n%s\nDiff:\n%s" % (
        len(readback), len(_MSG), _MSG, readback,
        pyIO.DiffBuffers(_MSG, readback, 'reference', 'readback')))

    led.Write(1)                # LED off
    # all pins will close on exit
    print 'Test OK.  Final log:\n%s' % self.log.getvalue()   # DEBUG


if __name__ == "__main__":
    unittest.main()
