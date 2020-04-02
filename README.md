pespad
======

PESPad allows you to use any device that can run a web browser to be used as a control pad for a Linux based operating systems. For example, you can use your mobile phone and tablet as separate controllers!!

![PESPAD GUI](http://www.mundayweb.com/html/_images/pespad.png)

Installation
------------

Install the python-pip package for your distribution first (if you don't have it already).

Then install the python-uinput module (if you don't have it already):

    sudo pip install python-uinput

Download PESPad:

    git clone git://github.com/neilmunday/pespad

Install PESPad (for operating systems using systemd):

    sudo mkdir /opt/pespad
    cd pespad
    sudo cp -r pespad.py web /opt/pespad
    sudo cp systemd/pespad.service /etc/systemd/system/pespad.service

Enabling PESPad Service
-----------------------

To start PESPad:

    sudo systemctl start pespad.service

To stop PESPad:

    sudo systemctl stop pespad.service

To start PESPad at boot time:

    sudo systemctl enable pespad.service

To disable PESPad at boot time:

    sudo systemctl disable pespad.service

Changing the port that PESPad listens on
----------------------------------------

By default, the PESPad service will lisent on port 80 of your Linux system. To change the port, please edit /etc/systemd/system/pespad.service and change the port number specified by the "-p" option to pespad.py in the ExecStart line.

Debugging
---------

To enable debug messages, please edit /etc/systemd/system/pespad.service and add "-v" to the Exec start line. Then restart the pespad service:

    sudo systemctl restart pespad.service

The log file can be found at: /var/log/pespad.log

Using PESPad
------------

Now that you have the PESPad service running, on your mobile/tablet point your web browser to http://YOUR_SERVER_IP and you should be presented with the PESPad GUI. Note: if you have instructed PESPad to use a port other than port 80, use the URL: http://YOUR_SERVER_IP:PORT

At the top left of the GUI, press the "Connect" button. All being well, you should now have a working joystick device!

To confirm, on your Linux system examine the contents of /dev/input and you should see a "js" device for each modbile/table that you have connected.

Enjoy!

Notes:
-----

After 30 minutes of inactivity a joystick will be automatically disconnected.

Acknowledgements:
-----------------

* HTTP server code based on code from: http://blog.wachowicz.eu/?p=256
* Daemon class based on code from: http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
* Sencha for their SenchaTouch 1.1 JavaScript framework

