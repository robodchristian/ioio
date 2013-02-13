#!/usr/bin/python
# Simple test case.  The "hello world" for pyIO.
# Hacked up to talk to IOIO by dchristian
# based on: rfcomm-client.py by Albert Huang <albert@csail.mit.edu> (part of pyBlueZ)
# simple IOIO connection over RFCOMM sockets demonstration

import sys, time

import pyIO
import digital_out
import ezlog

# More than 256
msg = '''The limerick packs laughs anatomical
In space that is quite economical.
But the good ones I've seen
So seldom are clean
And the clean ones so seldom are comical.

There was a young rustic named Mallory,
who drew but a very small salary.
When he went to the show,
his purse made him go
to a seat in the uppermost gallery.

There was a Young Person of Smyrna
Whose grandmother threatened to burn her*;
But she seized on the cat,
and said 'Granny, burn that!
You incongruous old woman of Smyrna!'
'''
msg = "hello world"

def main():
    addr = None
    ezlog.LogLevel(ezlog.WARN)

    if len(sys.argv) < 2:
        print "No bluetooth device specified.  Searching for the IOIO service..."
    else:
        addr = sys.argv[1]
        print "Searching for IOIO on %s" % addr

    conn = pyIO.IOIO()
    try:
      conn.WaitForConnect(addr)

      print "connected...  Ctrl-C to exit"
      count = 0
      led = conn.OpenDigitalOutput('LED', digital_out.MODE_NORMAL,
                                 count & 1)
      in1 = conn.OpenDigitalInput(1)
      out2 = conn.OpenDigitalOutput(2)
      uart1 = conn.OpenUart(6, 7, 57600) # 230400
      uart1.write(msg)
      while True:
        time.sleep(0.5)
        count += 1
        out2.Write(count&1)
        led.Write(count&1)
        ret = uart1.read()
        if ret:
          print "Read:", ret
        ii = in1.Read()
        if ii != (count&1):
          print "Output", count, "input", ii
    except (KeyboardInterrupt, SystemExit):
      pass

    print "closing"
    in1.Close()
    uart1.Close()
    conn.Disconnect()
    conn.WaitForDisconnect()


if __name__ == '__main__':
    main()
