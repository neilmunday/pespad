#!/usr/bin/env python2

#
#    This file is part of PESPad.
#
#    PESPad allows any device that can run a web browser to be used as
#    control pad for Linux based operating systems.
#
#    Copyright (C) 2014 Neil Munday (neil@mundayweb.com)
#
#    PESPad is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PESPad is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with PESPad.  If not, see <http://www.gnu.org/licenses/>.
#

"""
pespad will launch a HTTP 1.1 daemon on the chosen port of the host.
When a client connects they will be served a web base interface that
includes a control pad. Once a control pad has been requested, pespad
will try to create a new joystick device on the host using the uinput
Linux kernel module.

Button presses on the control pad in the browser will then be sent
to the joystick device and any programs that are listening for joystick
input will respond accordingly.

Each client is assigned their own joystick device.

pespad has been successfully used with the Pi Entertainment System,
available from http://pes.mundayweb.com

It has also been used with other Linux operating systems.

Note: if using with RetroArch, make sure you set the joystick driver
to "linuxraw".

Acknowledgements:

 HTTP server code based on code from: http://blog.wachowicz.eu/?p=256
 Daemon class based on code from: http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
 Sencha for their SenchaTouch 1.1 JavaScript framework
"""

import atexit
import argparse
import logging
import os
import sys
import signal
import socket
import time
import uinput
import signal
from signal import SIGTERM
import threading

CLIENT_TIMEOUT = 1800 # 30 mins
MAX_CLIENTS = 16 # max number of active clients

def shutdownServer(sig, dummy):
	global server
	if server:
		server.shutdown()
	logging.shutdown()
	sys.exit(0)

def stopDaemon(sig, dummy):
	global server
	if server:
		server.shutdown()

class Daemon(object):
	"""
	A generic daemon class.
	
	Usage: subclass the Daemon class and override the run() method
	"""
	def __init__(self, pidfile, loglevel, logfile=None, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
		self.__stdin = stdin
		self.__stdout = stdout
		self.__stderr = stderr
		self.__pidfile = pidfile
		self.__logfile = logfile
		self.__loglevel = loglevel
	
	def daemonize(self):
		"""
		Do the UNIX double-fork magic, see Stevens' "Advanced 
		Programming in the UNIX Environment" for details (ISBN 0201563177)
		http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
		"""
		try: 
			pid = os.fork() 
			if pid > 0:
				# exit first parent
				logging.shutdown()
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
			logging.shutdown()
			sys.exit(1)
	
		# decouple from parent environment
		os.chdir("/") 
		os.setsid() 
		os.umask(0) 
	
		# do second fork
		try: 
			pid = os.fork() 
			if pid > 0:
				# exit from second parent
				logging.shutdown()
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
			logging.shutdown()
			sys.exit(1) 
	
		# redirect standard file descriptors
		sys.stdout.flush()
		sys.stderr.flush()
		si = file(self.__stdin, 'r')
		so = file(self.__stdout, 'a+')
		se = file(self.__stderr, 'a+', 0)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
	
		# write pidfile
		atexit.register(self.delpid)
		pid = str(os.getpid())
		file(self.__pidfile,'w+').write("%s\n" % pid)
	
	def delpid(self):
		os.remove(self.__pidfile)

	def restart(self):
		"""
		Restart the daemon
		"""
		self.stop()
		self.start()

	def run(self):
		"""
		You should override this method when you subclass Daemon. It will be called after the process has been
		daemonized by start() or restart().
		"""

	def start(self):
		"""
		Start the daemon
		"""

		if self.__logfile:
			# remove old log file
			if os.path.exists(self.__logfile):
				os.remove(self.__logfile)
			logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', filename=self.__logfile, level=self.__loglevel)
			logging.debug("Created new log file")
		else:
			logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=self.__loglevel)
	
		if self.status():
			message = "pidfile %s already exist. Daemon already running?\n"
			sys.stderr.write(message % self.__pidfile)
			logging.shutdown()
			sys.exit(1)
		
		# Start the daemon
		self.daemonize()
		self.run()

	def status(self):
		# Check for a pidfile to see if the daemon already runs
		try:
			pf = file(self.__pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None

		if pid:
			return True
		return False

	def stop(self):
		"""
		Stop the daemon
		"""
		# Get the pid from the pidfile
		try:
			pf = file(self.__pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
	
		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			sys.stderr.write(message % self.__pidfile)
			return # not an error in a restart

		# Try killing the daemon process	
		try:
			while 1:
				os.kill(pid, SIGTERM)
				time.sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.__pidfile):
					os.remove(self.__pidfile)
			else:
				print str(err)
				logging.shutdown()
				sys.exit(1)

class Button(object):
	def __init__(self, uinputCode, pressed=False):
		self.__uinputCode = uinputCode
		self.__pressed = pressed

	def changeState(self):
		self.__pressed = not self.__pressed
		return self.__pressed

	def getCode(self):
		return self.__uinputCode

class Client(object):

	def __del__(self):
		logging.debug('Deleting Client object for %s' % self.__ip)
		del self.__device

	def __init__(self, ip):
		self.__ip = ip
		self.__device = uinput.Device([uinput.BTN_JOYSTICK, uinput.BTN_DPAD_UP, uinput.BTN_DPAD_DOWN, uinput.BTN_DPAD_LEFT, uinput.BTN_DPAD_RIGHT, uinput.BTN_START, uinput.BTN_SELECT, uinput.BTN_0, uinput.BTN_1, uinput.BTN_2, uinput.BTN_3, uinput.BTN_4, uinput.BTN_5, uinput.BTN_6, uinput.BTN_7, uinput.BTN_8, uinput.BTN_9], "pespad")
		self.__lastContact = int(time.time())

	def emit(self, btn, state):
		self.__device.emit(btn, state)

	def getDevice(self):
		return self.__device

	def getIp(self):
		return self.__ip

	def getLastContact(self):
		return self.__lastContact

	def updateContactTime(self):
		self.__lastContact = int(time.time())

class PESPadServer(Daemon):

	def __init__(self, port, pidfile, loglevel, logfile=None):
		super(PESPadServer, self).__init__(pidfile, loglevel, logfile)
		self.__host = ''
		self.__port = port
		self.__baseDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
		self.__webroot = self.__baseDir + os.sep + 'web'
		self.__checkDir(self.__webroot)
		self.__logfile = logfile
		self.__loglevel = loglevel
		self.__socket = None

		# BTN mappings:
		# BTN_JOYSTICK = Exit
		# 0 = Load state
		# 1 = Save state
		# 2 = A
		# 3 = B
		# 4 = X
		# 5 = Y
		# 6 = left shoulder
		# 7 = right shoulder
		# 8 = left shoulder 2
		# 9 = right shoulder 2

		self.__jsMap = {}
		self.__jsMap['exit'] = Button(uinput.BTN_JOYSTICK)
		self.__jsMap['start'] = Button(uinput.BTN_START)
		self.__jsMap['select'] = Button(uinput.BTN_SELECT)
		self.__jsMap['load'] = Button(uinput.BTN_0)
		self.__jsMap['save'] = Button(uinput.BTN_1)
		self.__jsMap['a'] = Button(uinput.BTN_2)
		self.__jsMap['b'] = Button(uinput.BTN_3)
		self.__jsMap['x'] = Button(uinput.BTN_4)
		self.__jsMap['y'] = Button(uinput.BTN_5)
		self.__jsMap['l1shoulder'] = Button(uinput.BTN_6)
		self.__jsMap['r1shoulder'] = Button(uinput.BTN_7)
		self.__jsMap['l2shoulder'] = Button(uinput.BTN_8)
		self.__jsMap['r2shoulder'] = Button(uinput.BTN_9)
		self.__jsMap['up'] = Button(uinput.BTN_DPAD_UP)
		self.__jsMap['down'] = Button(uinput.BTN_DPAD_DOWN)
		self.__jsMap['left'] = Button(uinput.BTN_DPAD_LEFT)
		self.__jsMap['right'] = Button(uinput.BTN_DPAD_RIGHT)

		self.__clients = {}
		self.__clientCleanUpThread = None

	def __checkDir(self, dir):
		if not os.path.exists(dir):
			self.__exit("Error: %s does not exist!" % dir)
		if not os.path.isdir(dir):
			self.__exit("Error: %s is not a directory!" % dir)

	def __createHeaders(self, code):
		s = ''
		if code == 200:
			s = "HTTP/1.1 200 OK\n"
		elif code == 404:
			s = "HTTP/1.1 404 Not Found\n"
		elif code == 500:
			s = "HTTP/1.1 500 Internal server error\n"

		s += "Date: " + time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()) + "\n"
		s += "Server: PES HTTP Server\n"
		s += "Connection: close\n\n"
		return s

	def createSocket(self):
		if self.__logfile:
			# remove old log file
			if os.path.exists(self.__logfile):
				os.remove(self.__logfile)
			logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', filename=self.__logfile, level=self.__loglevel)
			logging.debug("Created new log file")
		else:
			logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=self.__loglevel)

		# try to get the socket before daemonizing
		self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		i = 0
		acquired = False
		while i < 10:
			try:
				logging.info('Attempting to launching HTTP server on %s:%d' % (self.__host, self.__port))
				self.__socket.bind((self.__host, self.__port))
				logging.info('Success!')
				acquired = True
				break
			except Exception, e:
				logging.info("Could not acquire port %d (attempt #%d)" % (self.__port, i + 1))

			time.sleep(1)
			i += 1

		if not acquired:
			logging.critical("Could not acquire port after %d attempts!" % i)
			sys.stderr.write("Could not acquire port after %d attempts!\n" % i)
			sys.exit(1)

	def __exit(self, msg):
		print msg
		self.shutdown()
		logging.shutdown()
		sys.exit(1)

	def __listen(self):
		logging.info("Starting PESPad HTTP server")
		while True:
			logging.info("Waiting for connections...")
			self.__socket.listen(3) # no. of queued connections
			conn, addr = self.__socket.accept()
			ip = addr[0]
			logging.info("Got connection from %s" % ip)
			data = conn.recv(1024)
			s = bytes.decode(data)
			requestMethod = s.split(' ')[0]
			logging.debug("Method: %s" % requestMethod)
			logging.debug("Request body: %s" % s)

			if requestMethod == "GET" or requestMethod == "HEAD":
				content = ''
				f = s.split(' ')[1]
				f = f.split('?')[0] # ignore arguments

				if f[0:4] == '/js/':
					# handle remote joystick input
					btnStr = f[4:]
					if btnStr == 'connect':
						# a JS device has been requested
						if not ip in self.__clients:
							logging.info("Creating device for %s" % ip)
							try:
								self.__clients[ip] = Client(ip)
								content = "{ \"success\": true }\n"
							except Exception, e:
								logging.debug("Exception occurred when trying to create device:\n%s" % e)
								content = "{ \"success\": false, \"error\": \"Could not create uinput device!\" }"
						else:
							content = "{ \"success\": true }\n"
						headers = self.__createHeaders(200)
					elif btnStr == 'disconnect':
						headers = self.__createHeaders(200)
						if not ip in self.__clients:
							content = "{ \"success\": true }"
						else:
							self.removeClient(ip)
							content = "{ \"success\": true }"
					elif not btnStr in self.__jsMap:
						logging.debug("Unknown button: %s from %s" % (btnStr, ip))
						headers, content = self.__pageNotFound(f)
					else:
						headers = self.__createHeaders(200)
						if not ip in self.__clients:
							logging.info("No device found for %s - ignoring request" % ip)
							headers = self.__createHeaders(200)
							content = "{ \"success\": false, \"error\": \"Device not recognised, please refresh your browser\" }\n"
						else:
							btn = self.__jsMap[btnStr]
							logging.debug("%s button press processed for %s" % (btnStr, ip))
							self.__clients[ip].emit(btn.getCode(), int(btn.changeState()))
							content = "{ \"success\": true }\n"
				else:
					if f == '/':
						f = '/index.html'

					f = self.__webroot + f
					logging.debug("Serving file: %s" % f)
					try:
						if requestMethod == 'GET':
							handler = open(f, 'rb')
							content = handler.read()
							handler.close()
						headers = self.__createHeaders(200)
					except Exception, e:
						logging.info("File %s not found" % f)
						headers, content = self.__pageNotFound(f)

				response = headers.encode()
				if requestMethod == "GET":
					response += content

				conn.send(response)
				logging.debug("Closing connection to client")
				conn.close()
			else:
				logging.info("Unknown/unsupported request method: %s" % requestMethod)

	def getClients(self):
		return self.__clients

	def __pageNotFound(self, f):
		headers = self.__createHeaders(404)
		content = b"<html><head><title>File not found</title><head><body>File %s not found on this server</body></html>" % f
		return (headers, content)

	def removeClient(self, ip):
		if ip in self.__clients:
			logging.info('Removing joystick device for client %s' % ip)
			del self.__clients[ip]

	def restart(self):
		sys.stderr.write("restart operation is not supported by PASPad server. Please stop the server yourself and then try to restart. This is beause the port takes time to free\n")

	def run(self):
		if not self.__socket:
			logging.critical("socket not created - did you call createSocket first?")
			logging.shutdown()
			sys.exit(1)

		# start client cleanup thread
		self.__clientCleanUpThread = ClientCleanUpThread(self)
		self.__clientCleanUpThread.start()
		self.__listen()

	def shutdown(self):
		try:
			logging.debug('Stopping clean up thread...')
			if self.__clientCleanUpThread:
				self.__clientCleanUpThread.stop()
			logging.info('Stopping the server...')
			self.__socket.shutdown(socket.SHUT_RDWR)
			logging.info('Success!')
		except Exception, e:
			logging.warning('Failed to shutdown the socket!')	

	def start(self):
		if self.status():
			message = "pidfile %s already exist. Daemon already running?\n"
			sys.stderr.write(message % self.__pidfile)
			logging.shutdown()
			sys.exit(1)

		self.createSocket()
		self.daemonize()
		self.run()

class ClientCleanUpThread(threading.Thread):
	def __init__(self, server):
		threading.Thread.__init__(self)
		self.__stop = False
		self.__sleep = 10
		self.__server = server
		logging.debug('ClientCleanUpThread created')

	def run(self):
		logging.debug('ClientCleanUp thread started')

		while True:
			if self.__stop:
				logging.debug('ClientCleanUp thread stopped')
				return

			now = time.time()

			clients =  self.__server.getClients()
			logging.debug('Checking %d client(s) for recent activity' % len(clients))

			clientsToDelete = [] # can't modify dictionary whilst iterating over it so use a list to store candidates

			client = None

			for client in clients.itervalues():
				ip = client.getIp()
				if now - client.getLastContact() > CLIENT_TIMEOUT:
					clientsToDelete.append(ip)
				else:
					logging.debug('Client %s is still active' % ip)

			del client # remove reference to object so that it can be delete later

			if len(clientsToDelete) > 0:
				for ip in clientsToDelete:
					self.__server.removeClient(ip)

			time.sleep(self.__sleep)


	def stop(self):
		self.__stop = True

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Launch the PESPad server', add_help=True)
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	parser.add_argument('-p', '--port', help='Listen on this port', type=int, dest='port', default=80)
	parser.add_argument('-l', '--log', help='File to log messages to', type=str, dest='logfile')
	parser.add_argument('-d', '--daemon', help='Run PESPad as a daemon', dest='daemon', choices=['start', 'stop', 'status'])
	args = parser.parse_args()

	if args.daemon and not args.logfile:
		sys.stderr.write("Please specify a log file when running as a daemon\n")
		sys.exit(1)

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG
	
	pidfile = '/tmp/pespad.pid'

	server = PESPadServer(args.port, pidfile, logLevel, args.logfile)

	if args.daemon:
		if args.daemon == 'start':
			#signal.signal(signal.SIGTERM, stopDaemon)
			server.start()
		elif args.daemon == 'stop':
			server.stop()
		elif args.daemon == 'status':
			if server.status():
				print "Server is running"
			else:
				print "Server is not running"
	else:
		signal.signal(signal.SIGTERM, shutdownServer)
		signal.signal(signal.SIGINT, shutdownServer)
		server.createSocket()
		server.run()

	logging.shutdown()
	sys.exit(0)

