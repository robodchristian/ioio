#!/usr/bin/python
# Use IOIO to monitor serial ports
# Somewhat related to Serial Talk (stalk)

import os, optparse
import sys

import select                   # Need something different on Windows

try:
  import tty, termios           # Unix only
except ImportError:
  print "Error importing tty.  Continuing..."
  tty = None

import pyIO
import digital_out
import uart


def HandleArgs(args):
  """Setup argument parsing and return parsed arguments."""
  parser = optparse.OptionParser(usage="Connect to an IOIO's serial port")
  parser.add_option(
      "-b", "--baud", type="int", help="Baud rate", dest="baud", default=115200)
  parser.add_option(
      "-p", "--pins", type="string", help="Pins: RX,TX[,RTX,CTS]", dest="pins",
      default="40,39,46,45")
  parser.add_option(
      "-i", "--ioio", type="string", help="IOIO address", dest="ioio")

  options, pos_args = parser.parse_args(args)

  if not options.ioio:          # try environment variable
    options.ioio = os.getenv('IOIO')

  if options.pins:              # turn pins into a list
    print "pins1", options.pins
    options.pins = options.pins.split(',')
    print "pins2", options.pins

  for nn in range(len(options.pins)):
    options.pins[nn] = int(options.pins[nn].strip())

  return (options, pos_args)


def main():
  options, pos_args = HandleArgs(sys.argv)
  conn = pyIO.IOIO()
  on = 0
  off = 1
  if not len(options.pins) in (2, 4):
    print "Error parsing pins: %s" % ','.join(map(str, options.pins))
    print "Expected either 2 or 4 pins.  e.g. 3,4 or 3,4,5,6"
    return

  print "Waiting for connection to IOIO at %s" % options.ioio
  if tty:
    old_settings = termios.tcgetattr(sys.stdin)
  try:
    conn.WaitForConnect(options.ioio)

    print "connected...  Ctrl-C to exit"
    led = conn.OpenDigitalOutput('LED', digital_out.MODE_NORMAL, on)

    if len(options.pins) == 2:
      print "Opening Uart RX=%d TX=%d baud: %d" % (
          options.pins[0], options.pins[1], options.baud)
      uart1 = conn.OpenUart(options.pins[0], options.pins[1], options.baud)
    elif len(options.pins) == 4:
      print "Opening Uart RX=%d TX=%d RTS=%d CTS=%d baud: %d" % (
          options.pins[0], options.pins[1], options.pins[2], options.pins[3], options.baud)
      uart1 = conn.OpenUart(options.pins[0], options.pins[1], options.baud,
                            flow=uart.FLOW_RTSCTS,
                            rts_pin=options.pins[2], cts_pin=options.pins[3])
    else:
      print "Failed to parse pin configuration: %r" % options.pins
      return

    if tty:
      tty.setraw(sys.stdin)
      tty.setraw(sys.stdout)    # seems to also set stdin

    count = 0
    while True:
      readable = [sys.stdin]
      (readable, w, x) = select.select(readable, [], [], 0.01)
      if readable:
        c = sys.stdin.read(1)
        # TODO: make this Ctrl-] (chr(29)) and handle next character properly
        if c == chr(3):         # Ctrl-C
          print "^C\r\n",
          break
        else:
          uart1.write(c)
      ret = uart1.read()        # no argument is non-blocking
      if ret:
        count += 1
        sys.stdout.write(ret)
        sys.stdout.flush()
        led.Write(count &1)
  except (KeyboardInterrupt, SystemExit):
    pass
  finally:
    if tty:
      termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

  print "closing", count
  led.Write(off)
  uart1.Close()
  conn.Disconnect()
  conn.WaitForDisconnect()


if __name__ == '__main__':
    main()
