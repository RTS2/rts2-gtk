#!/usr/bin/env python

import gtk
from rts2ui import Rts2Command
import login

class OnOffStandby(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		self.b = gtk.HButtonBox()
		self.b.pack_start(Rts2Command('centrald','off',label='Off'))
		self.b.pack_start(Rts2Command('centrald','standby',label='Standby'))
		self.b.pack_start(Rts2Command('centrald','on',label='On'))

		self.add(self.b)
		self.show_all()

if __name__ == '__main__':
	l = login.Login()
	l.signon()

	w = OnOffStandby()
	gtk.main()
