#!/usr/bin/env python
#
# Status bar - display 
#
# Petr Kubanek <petr@kubanek.net>

import gtk
import gettext
import gobject
import time

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class StatusBox(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)
		self.pb = gtk.ProgressBar()
		self.te = gtk.Label()

		self.pack_start(self.pb,True)
		self.pack_start(gtk.VSeparator(),False,False)
		self.pack_end(self.te,False,False)
		self.show_all()
		
		gobject.timeout_add(500,self.timer)

	def set_fraction(self,fr,messagetext=''):
		self.pb.set_fraction(fr)
		self.pb.set_text(messagetext)

	def message(self,messagetext):
		self.pb.pulse()
		self.pb.set_text(messagetext)
		return False

	def timer(self):
		self.te.set_text(time.ctime())
		self.pb.pulse ()
		return True

	def set_action(self,action_name):
		self.pb.set_text(action_name)
		self.pb.pulse ()

