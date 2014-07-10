#!/usr/bin/env python
#
# Login dialog. Login to RTS2 XML-RPC server and JSON server.
#
# Petr Kubanek <petr@kubanek.net

import rts2config

# Test and import GTK
import pygtk
import gtk
import gobject
import glib
gtk.init_check()
gtk.gdk.threads_init()

import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

# for JSON
import rts2.json
import sys
import signal
import re
import threading
import Queue

import urlparse
import urllib

"""Returns singleton for JSON calls."""
def getProxy():
	global __jsonProxy
	return __jsonProxy	

def getHostString(host, login, password):
	return 'http://' + login + ':' + password + '@' + host

class ProgressDialog(gtk.Dialog):
	def __init__(self, parent):
		gtk.Dialog.__init__(self, 'Progress', parent, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
		self.description = gtk.Label()
		self.pb = gtk.ProgressBar()

		self.vbox.pack_start(self.description, False, False)
		self.vbox.pack_end(self.pb, False, False)

		self.connect('response', ProgressDialog.response)

		gobject.idle_add(self.show_all)

	def set_description(self, description, progress, total):
		self.description.set_label(description)
		if total:
			self.pb.set_fraction(float(progress) / total)
	
	def response(self, response_id):
		if response_id == gtk.RESPONSE_REJECT:
			def __cancel(self):
				self.description.set_label('Canceling')
				self.pb.set_fraction(0)
				getProxy().clear_queue()
				self.pb.set_fraction(1)
				self.hide()

			gobject.idle_add(__cancel, self)

class JSONProxy(rts2.json.JSONProxy):
	def __init__(self, url, login, password, verbose=False):
		rts2.json.JSONProxy.__init__(self, url=url, username=login, password=password, verbose=verbose)

		self.__queue = Queue.Queue()
		self.description = None

		self.progress_dialog = None
		self.progress = 0
		self.total = 0

	def getSelectionComboEntry(self, device, name, active=0):
		ret = gtk.combo_box_entry_new_text()
		for x in self.getSelection(device, name):
			ret.append_text(x)
		ret.set_active(active)
		return ret

	def startQueue(self):
		def __queue(self):
			while True:
				(task, description, args, kwargs) = self.__queue.get()
				if self.progress_dialog:
					self.progress += 1
					gobject.idle_add(self.progress_dialog.set_description, description, self.progress, self.total)
				task(*args, **kwargs)
				self.__queue.task_done()
				if self.progress_dialog and self.progress >= self.total:
					def __close(self):
						if self.progress_dialog is not None:
							self.progress_dialog.hide()
							self.progress_dialog.get_transient_for().window.set_cursor(None)
							self.progress_dialog = None
					gobject.idle_add(__close, self)

		t = threading.Thread(target=__queue, args=(self,))
		t.daemon = True
		t.start()

	def queue(self, task, description, *args, **kwargs):
		if self.progress_dialog:
			self.total += 1
		self.__queue.put((task, description, args, kwargs))
	
	def show_progress_dialog(self, parent):
		if self.progress_dialog is None:
			self.progress = 0
			self.total = 0
			self.progress_dialog = ProgressDialog(parent)
		def __show(self, parent):
			parent.window.set_cursor (gtk.gdk.Cursor(gtk.gdk.WATCH))
			self.progress_dialog.show()
		
		gobject.idle_add(__show, self, parent)

	def clear_queue(self):
		"""Clear queue."""
		try:
			while True:
				task = self.__queue.get(False)
				self.__queue.task_done()
		except Queue.Empty:
			pass
	
def createJsonServer(host, login, password, verbose=False):
	global __jsonProxy
	__jsonProxy = JSONProxy(host, login, password, verbose=verbose)
	rts2.json.set_proxy(__jsonProxy)

class Login:
	"""Login window. Creates login window, ask user for credetials. If login is
	successfull, creates XML-RPC proxy and issues login request to it."""
	def __init__(self):
		signal.signal(signal.SIGINT,signal.SIG_DFL)

		self.dialog = gtk.Dialog(title=_('Please login'),flags=gtk.DIALOG_DESTROY_WITH_PARENT,buttons=(gtk.STOCK_CONNECT,1,gtk.STOCK_QUIT,2))

		self.config = rts2config.Config()

		self.server = gtk.combo_box_entry_new_text()
		self.server.connect('changed',self.server_changed)
		self.login = gtk.Entry(10)
		self.password = gtk.Entry(10)
		self.password.set_visibility(False)

		self.verbose = gtk.CheckButton()
		self.verbose.set_active(False)

		self.server_list = self.config.get_list('hosts')
		if (len(self.server_list) == 0):
			self.server.append_text('localhost:8889')
			self.server.set_active(0)
		else:
		  	for ser in self.server_list:
				self.server.append_text(ser)
			i = self.config.get_int('last_host')
			self.server.set_active(i)
			(log,pas) = self.config.get_pair('users/' + self.__server_name(self.server.get_active_text()))
			self.login.set_text(log)
			self.password.set_text(pas)

		logt = gtk.Table(2,4)
		logt.attach(self.server,1,2,0,1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(self.login,1,2,1,2,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(self.password,1,2,2,3,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(self.verbose,1,2,3,4,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)

		class NameLabel(gtk.Label):
			def __init__(self,str=None):
				gtk.Label.__init__(self,str)
				self.set_alignment(0,0.5)

		logt.attach(NameLabel(_('Server:')),0,1,0,1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(NameLabel(_('User name:')),0,1,1,2,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(NameLabel(_('Password:')),0,1,2,3,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		logt.attach(NameLabel(_('Verbose:')),0,1,3,4,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)

		self.pb=gtk.ProgressBar()
		logt.attach(self.pb,0,2,4,5,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)

		self.dialog.vbox.pack_start(logt)

	def server_changed(self,b):
		if self.config.gconf:
			try:
				(l,p) = self.config.get_pair('users/' + self.__server_name(self.server.get_active_text()))
				if l is None:
					l = ''
				if p is None:
					p = ''
				self.login.set_text(l)
				self.password.set_text(p)
			except glib.GError,er:
				pass

	def add_server(self):
		self.__login_status = -2  # 0 ... success, 1.. retry, -1 .. exit
		try:
			createJsonServer(self.server.get_active_text(), self.login.get_text(), self.password.get_text(), verbose=self.verbose.get_active())
			getProxy().loadJson('/api/devices')
			if self.config.gconf:
				# sucessfull login. let's see if server is present in the list..
				try:
					self.config.set_int('last_host', self.server_list.index(self.server.get_active_text()))
					self.config.set_pair('users/' + self.__server_name(self.server.get_active_text()), self.login.get_text(), self.password.get_text())
				except ValueError,v:
					try:
						gtk.gdk.threads_enter()
						msgbox = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_("Do you want to add {0}@{1} to the list of saved servers?").format(self.login.get_text(),self.server.get_active_text(),self.login.get_text()))
						if msgbox.run() == gtk.RESPONSE_YES:
						  	self.server_list.append(self.server.get_active_text())
							self.config.set_list('hosts', self.server_list)
							self.config.set_int('last_host', len(self.server_list) - 1)
							self.config.set_pair('users/' + self.__server_name(self.server.get_active_text()), self.login.get_text(), self.password.get_text())
						msgbox.hide()
					finally:
						gtk.gdk.threads_leave()
			self.__login_status = 0

		except Exception,ex:
			try:
				gtk.gdk.threads_enter()
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_YES_NO, message_format=_("There was problem connecting to RTS2 server at {0}:{1}. Do you want to try again?").format(self.server.get_active_text(),ex))
				ret = msgbox.run()
				msgbox.hide()
				if ret == gtk.RESPONSE_YES:
					self.__login_status = 1
				else:
					self.__login_status = -1
			finally:
				gtk.gdk.threads_leave()

	def run(self):
		while True:
			i = self.dialog.run()
			if (i == 1):
				t = threading.Thread(target=self.add_server)
				t.start()
				while t.is_alive():
					gtk.main_iteration(False)
				t.join()
				if self.__login_status <= 0:
					return self.__login_status

	def message(self,message):
		self.pb.set_text(message)

	def signon(self, url='localhost:8889', login=None, password=None, startQueue=False, verbose=False):
		"""Sign on to RTS2 JSON server. url - JSON API URL (can include username and login)"""
		# try to get username (and password) from url
		purl = urlparse.urlsplit(url)
		userpass,host = urllib.splituser(purl.netloc)
		(userpass, netloc) = urllib.splituser(purl.netloc)
		if userpass is not None:
			(login, password) = urllib.splitpasswd(userpass)
			url = netloc + purl.path
			if purl.query:
				url += '?' + query
			if purl.fragment:
				url += '#' + fragment

		if login is None:
		  	self.verbose.set_active(verbose)
			self.dialog.show_all()
			if self.run():
				self.dialog.hide()
				sys.exit(-1)
			self.dialog.hide()
		else:
			# or just create server..
			createJsonServer(url, login, password, verbose=verbose)
			getProxy().loadJson('/api/devices')
		if startQueue:
			getProxy().startQueue()
		getProxy().refresh()

	def __server_name(self,server):
		"""Return name of server strip by ending / and other characters, which causes problems for gconf"""
		return re.sub('[^a-zA-Z0-9]+$','',server)

# test JSOn routines
# assumes that SD device is available as dummy sensor
if __name__ == '__main__':
	l = Login()
	l.signon()
	getProxy().executeCommand('SD','add 5')
	print getProxy().getValue('SD','test_content1')
	print getProxy().getValue('SD','test_content2')
