# Copyright 2012 Google Inc. All rights reserved

"""the exception classes for pyIO"""


class IOException(Exception):
  """Communication error."""
  pass


class ConnectionLostException(Exception):
  """Connection no longer valid."""
  pass


class IncompatibilityException(Exception):
  """Unable to interact with given firmware."""
  pass


class IllegalStateException(Exception):
  """Connection not valid."""
  pass


class IllegalArgumentException(Exception):
  """Invalid arguments given."""
  pass
