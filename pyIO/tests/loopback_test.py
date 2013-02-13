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

# This is long enough for multiple sends and flow control
_MSG = '''The limerick packs laughs anatomical
In space that is quite economical.
But the good ones I've seen
So seldom are clean
And the clean ones so seldom are comical.

        ~!@#$%^&*()_+[];',./-={}|:"<>?

There was a young rustic named Mallory,
who drew but a very small salary.
When he went to the show,
his purse made him go
to a seat in the uppermost gallery.

There was a Young Person of Smyrna
Whose grandmother threatened to burn her
But she seized on the cat,
and said 'Granny, burn that!
You incongruous old woman of Smyrna!'
'''

# Note: bluetooth address must be passed in throught IOIO
class SimpleTests(unittest.TestCase):

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

  def testLoopback(self):
    """Test loopback of various devices."""
    led = self.conn.OpenDigitalOutput('LED')
    self.assertTrue(led != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    led.Write(0)                # LED on

    in1 = self.conn.OpenDigitalInput(1)
    self.assertTrue(in1 != None,
                    "Expected digital_in object.  log=\n%s" % self.log.getvalue())

    out2 = self.conn.OpenDigitalOutput(2)
    self.assertTrue(out2 != None,
                    "Expected digital_out object.  log=\n%s" % self.log.getvalue())
    for ref in (True, False, True, False):
      out2.Write(ref)
      data = in1.WaitForValue(ref, timeout=1.0)
      self.assertEqual(ref, data, "Read back %r != %r" % (data, ref))

    # We dump many things in one test because the connect can be slow

    uobj = self.conn.OpenUart(6, 7, 250000)
    self.assertTrue(uobj != None,
                    "Expected uart object.  log=\n%s" % self.log.getvalue())
    uobj.write(_MSG)
    time.sleep(0.1) # enough time for first chunk to be written and then read
    readback = ''
    eof_count = 0
    while eof_count < 3:
      chunk = uobj.read()
      if not chunk:
        eof_count += 1
        time.sleep(0.1)
        continue
      else:
        eof_count = 0
      readback += chunk
    self.assertEqual(_MSG, readback, "Read back %d != msg %d" % (len(readback), len(_MSG)))

    led.Write(1)                # LED off
    self.conn.SoftReset()
    # all pins will close on exit
    print 'Test OK.  Final log:\n%s' % self.log.getvalue()   # DEBUG


if __name__ == "__main__":
    unittest.main()
