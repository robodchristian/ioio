#!/usr/bin/env python
"""For this test case, jumper 1-2, and 6-7."""

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
    #import uart
except ImportError:
    print "Unable to load pyIO."
    print "Try: PYTHONPATH=. IOIO='00:1F:81:00:08:30' tests/simple_test.py"
    sys.exit(1)


# Note: bluetooth address must be passed in throught IOIO
class ResetTests(unittest.TestCase):

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

  def testReset(self):
    """Test loopback of various devices."""
    print "Doing reset"
    self.conn.HardReset()
    time.sleep(0.1)
    self.conn = None
    self.conn = pyIO.IOIO()
    addr = os.getenv('IOIO')
    self.conn.WaitForConnect(addr)
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    led.Write(0)                # LED on
    led.Write(1)                # LED off
    print 'Test OK.  Final log:\n%s' % self.log.getvalue()   # DEBUG


if __name__ == "__main__":
    unittest.main()
