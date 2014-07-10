"""Widget which display rotator properties."""

import time
import gtk
import gobject
import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

import login
from gtkradec import Ra,Dec,RaDec,AltAz
import radec

class Rotator(gtk.Frame):
	r = 0
	def __init__(self):
		gtk.Frame.__init__(self,_("Rotator"))
		vbox = gtk.VBox()
		self.t=gtk.Table(2,4)
		
		self.t.set_col_spacing(0,5)

		self.rot1 = gtk.Entry()
		self.rot2 = gtk.Entry()

		self.instr1 = gtk.RadioButton(None,'1')
		self.instr2 = gtk.RadioButton(self.instr1,'2')

		self.add_rts2_value(_('Rotator 1'),self.rot1)
		self.add_rts2_value(_('Rotator 2'),self.rot2)

		self.instrb = gtk.HBox()
		self.instrb.pack_start(self.instr1)
		self.instrb.pack_end(self.instr2)

		self.add_rts2_value('Instrument', self.instrb)

		bb = gtk.HButtonBox()
		bb.set_layout(gtk.BUTTONBOX_SPREAD)

		self.rot1 = gtk.Button(_('Set rotator 1'))
		self.rot2 = gtk.Button(_('Set rotator 2'))

		bb.pack_start(self.rot1)
		bb.pack_end(self.rot2)

		vbox.pack_start(self.t)
		vbox.pack_start(bb, False)

		self.add(vbox)
		self.show_all()

	def add_rts2_value(self,str,object):
		l = gtk.Label(str)
		l.set_alignment(0,0.5)
		self.t.attach(l,0,1,self.r,self.r+1)
		self.t.attach(object,1,2,self.r,self.r+1)
		self.r+=1
