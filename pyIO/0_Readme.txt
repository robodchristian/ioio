This is a pure Python port of the IOIO host software stack.  The
original software is here: https://github.com/ytai/ioio/wiki

Written by: Dan Christian
Started:  19 Sept 2012


* Goals *

Run with no emulator and fast startup.  Be able to talk to an IOIO
without the Android/Eclipse/Jave software stack.

Be able to support Linux, MacOSX, Windows 7, and Android.  Only Linux
for now.

Be able to talk over BlueTooth or USB (OTG mode).  Only BT for now.

Be able to talk to multiple IOIOs from the same script.

Keep the application level API as similar to the Java as is practical.


* Non-Goals *

Replace the IOIO-Manager.  This could be done, but it's easy enough to
just do firmware updates using Android.

Copy the internal structure of the Java libraries.


* Status *

Trivial operation over BlueTooth from Linux is currently possible.  

It isn't clear if the Windows XP support in PyBluez will extend to
Windows 7 (never tried).

There currently isn't any MacOSX support in PyBluez.  However,
python-lightblue http://lightblue.sourceforge.net/ does support Mac
and may help to add support to Bluez.


* Bugs *

Because this is a port of the C-Java communications protocol, effort
will be required to keep it in sync with the firmware.  There isn't
any easy way to automatically maintain sync.  A good test suite should
minimize the problems.

Many pin modes of the Java code are yet to be ported.  I only ported
the parts I needed: digital in, digital out, uart.  The architectures
should be complete enough that the other functions will be easy to
add.

The interface is not currently threadsafe.  Not hard to do, but not
needed so far.
