"""Widget which display telescope properties."""

import time
import gtk
import gobject
import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

import login
from gtkradec import Ra,Dec,RaDec,AltAz
import radec

class Telescope(gtk.Frame):
	r = 0
	def __init__(self,telescope_name):
		gtk.Frame.__init__(self,_("Telescope"))
		vbox = gtk.VBox()
		self.t=gtk.Table(2,4)
		self.telescope_name = telescope_name

		self.t.set_col_spacing(0,5)

		self.ori = RaDec()
		self.offs = RaDec()
		self.tar = RaDec()
		self.tel = RaDec()

		self.ha = Ra()
		self.lst = Ra()

		self.add_rts2_value(_('Originator'),self.ori)

		ee = gtk.Entry()
		ee.set_text('2000.0')

		self.local_time = gtk.Label()
		self.universal_time = gtk.Label()
		self.julian_date = gtk.Label()
		self.altaz = AltAz()

		self.zenith_distance = gtk.Label()
		self.airmass = gtk.Label()

		self.add_rts2_value(_('Coordinates epoch'),ee)
		self.add_rts2_value(_('Offsets'),self.offs)
		self.add_rts2_value(_('Target'),self.tar)
		self.add_rts2_value(_('Telescope'),self.tel)

		self.add_rts2_value(_('Horizontal coordinates'),self.altaz)
		self.add_rts2_value(_('Zenith distance'),self.zenith_distance)
		self.add_rts2_value(_('Airmass'),self.airmass)

		self.add_rts2_value(_('Local time'),self.local_time)
		self.add_rts2_value(_('Universal time'),self.universal_time)
		self.add_rts2_value(_('Local sidereal time'),self.lst)

		self.add_rts2_value(_('Julian date'),self.julian_date)

		bb = gtk.HButtonBox()
		bb.set_layout(gtk.BUTTONBOX_SPREAD)

		bb2 = gtk.HButtonBox()
		bb2.set_layout(gtk.BUTTONBOX_SPREAD)

		self.worm = gtk.ToggleButton(_('Sidereal drive'))
		self.worm.connect('clicked',self.set_track)

		self.park = gtk.Button(_('Park'))
		self.park.connect('clicked',self.call_park)

		self.reset = gtk.Button(_('Reset'))
		self.reset.connect('clicked',self.call_reset)

		bb.pack_start(self.worm)
		bb.pack_end(self.park)
		bb2.pack_end(self.reset)

		vbox.pack_start(self.t)
		vbox.pack_start(bb, False)
		vbox.pack_end(bb2, False)

		self.add(vbox)
		self.show_all()

		gobject.timeout_add(500,self.refresh)

	def add_rts2_value(self,str,object):
		l = gtk.Label(str)
		l.set_alignment(0,0.5)
		self.t.attach(l,0,1,self.r,self.r+1)
		self.t.attach(object,1,2,self.r,self.r+1)
		self.r+=1

	def refresh(self):
		try:
			login.getProxy().executeCommand(self.telescope_name,'info')
			self.ori.set_string_radec(login.getProxy().getValue(self.telescope_name,'ORI'))
			self.offs.set_string_radec(login.getProxy().getValue(self.telescope_name,'OFFS'))
			self.tar.set_string_radec(login.getProxy().getValue(self.telescope_name,'TAR'))
			self.tel.set_string_radec(login.getProxy().getValue(self.telescope_name,'TEL'))
			#self.worm.set_active(login.getProxy().getValue(self.telescope_name,'TRACKING'))
			self.ha.set_ra(login.getProxy().getValue(self.telescope_name,'HA'))
			self.lst.set_ra(login.getProxy().getValue(self.telescope_name,'LST'))

			self.altaz.set_string_altaz(login.getProxy().getValue(self.telescope_name,'TEL_'))

			self.local_time.set_text(time.strftime('%D %H:%M:%S.25', time.localtime(login.getProxy().getValue(self.telescope_name,'infotime'))))
			self.universal_time.set_text(time.strftime('%D %H:%M:%S.25', time.gmtime(login.getProxy().getValue(self.telescope_name,'infotime'))))

			self.airmass.set_text(str(login.getProxy().getValue(self.telescope_name,'AIRMASS')))
			self.zenith_distance.set_text(radec.dec_string(90 - float(login.getProxy().getValue(self.telescope_name,'TEL_')['alt'])))
			self.julian_date.set_text(str(login.getProxy().getValue(self.telescope_name,'JULIAN_DAY')))
		except Exception, fault:
			print fault
		return True
	
	def set_track(self,widget):
		r = 'true'
		if self.worm.get_active() == False:
			r = 'false'
		login.getProxy().setValue(self.telescope_name,'TRACKING',r)
		login.getProxy().executeCommand(self.telescope_name,'info')
	
	def call_park(self,widget):
		login.getProxy().executeCommand(self.telescope_name,'park')

	def call_reset(self,widget):
		login.getProxy().executeCommand(self.telescope_name,'reset')
