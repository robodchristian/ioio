# Copyright 2012 Google Inc. All rights reserved

# IOIO connection over Bluetooth RFCOMM sockets
# Hacked up from pyBlueZ rfcomm-client.py by Albert Huang <albert@csail.mit.edu>

"""Connect to an IOIO over Bluetooth."""

from bluetooth import *         # pyBluez

# TODO: have a common main connection class
class BluetoothConnection(object):
  def __init__(self):
    """Create IOIO communication object.
    Do not reuse after Connect() succeeds.  Create a new object if needed.
    """
    self.sock = None            # the socket
    self.srv_name = None        # service name
    self.host = None            # host
    self.port = None            # port number

  def Find(
      self,
      addr = None,                                   # host address
      uuid = "00001101-0000-1000-8000-00805F9B34FB", # standard serial port device
      ):
    """Find the service, but don't connect."""
    service_matches = find_service( uuid = uuid, address = addr )

    if len(service_matches) == 0:
      return None

    first_match = service_matches[0]
    self.port = first_match["port"]
    self.srv_name = first_match["name"]
    self.host = first_match["host"]
    return (self.host, self.srv_name, self.port)

  def Connect(self):
    """Connect to service previously found."""
    # Create the client socket
    self.sock = BluetoothSocket( RFCOMM )
    self.sock.connect((self.host, self.port))

  def Disconnect(self):
    """Disconnect socket connection.
    The object should not be used after this.  Create a new one if needed.
    """
    if self.sock:               # TODO: handle SysError?
      self.sock.close()
    self.sock = None

  def CheckState(self):
    """Return true if connected."""
    return not not self.sock

  def _Read(self, max_len=1024):
    """Read raw data from connection (up to max_len)."""
    data = self.sock.recv(max_len)
    return data

  def _Send(self, data):
    """Send raw data over connection."""
    n = self.sock.send(data)
    # TODO: retry or show error if n != len(data)
    return n
