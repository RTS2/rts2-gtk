# Class for RTS2 entry widget
# It is connected so it will call rts2.value.set when user change value.
#
# (C) 2009 Petr Kubanek <petr@kubanek.net>

import login
import gtk

class Rts2Value(gtk.Entry):
	def __init__(self, device, value):
		gtk.Entry.__init__(self)
		self.set_text(str(login.jsonProxy().getValue(device,value)))
		self.connect('focus-out-event', self.focus_out_event)
		self.device = device
		self.value = value
	
	def focus_out_event(self, widget, event):
		login.jsonProxy().setValue(self.device,self.value,self.get_text())
