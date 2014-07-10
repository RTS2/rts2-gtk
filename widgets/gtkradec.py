#
# Module for drawing Ra Dec entry box
#
# Copyright (C) 2009 Petr Kubanek <petr@kubanek.net>

import gtk
import string
import math
from radec import *

class Ra(gtk.Entry):
    """Holds RA"""
    def __init__(self,sep=':'):
       gtk.Entry.__init__(self)
       self.sep=sep
       self.set_ra(0)

    def set_ra(self, ra):
       self.set_text(ra_string(ra,self.sep))

    def get_ra(self):
       return from_hms(self.get_text())*15

class Dec(gtk.Entry):
    """Holds DEC"""
    def __init__(self,sep=':'):
       gtk.Entry.__init__(self)
       self.sep=sep
       self.set_dec(0)

    def set_dec(self, dec):
       self.set_text(dec_string(dec,self.sep))

    def get_dec(self):
       return from_hms(self.get_text())


class RaDec(gtk.Entry):
    """Holds informations about Ra and Dec of the object."""
    def __init__(self):
       gtk.Entry.__init__(self)
       self.set_radec(0,0)

    def set_radec(self,ra,dec):
       ra = float(ra) / 15.0
       (signra,rah,ram,ras) = to_hms(ra)
       (signdec,dech,decm,decs) = to_hms(dec)
       self.set_text("%02i:%02i:%06.3f %c%02i:%02i:%05.2f" % (rah, ram, ras, signdec, dech, decm, decs))

    """Set value from string returned by RTS2. Both RA and DEC are in degrees,
    separated by space."""
    def set_string_radec(self,val):
	self.set_radec(val["ra"],val["dec"])

    def get_radec(self):
       # split on + or -
       try:
           (ra,dec) = string.split(self.get_text(),"+")
	   sign = 1
       except ValueError:
           try:
	       (ra,dec) = string.split(self.get_text(),"-")
	       sign = -1
	   except ValueError:
	       msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format="Cannot parse RADEC string " + self.get_text())
	       msgbox.run()
	       msgbox.hide()
	       return
       return (from_hms(ra)*15, sign * from_hms(dec))

class AltAz(gtk.Entry):
    """Holds informations about altitude and azimuth of the object."""
    def __init__(self):
       gtk.Entry.__init__(self)
       self.set_altaz(0,0)

    def set_altaz(self,alt,az):
       (signalt,alth,altm,alts) = to_hms(alt)
       (signaz,azh,azm,azs) = to_hms(az)
       self.set_text("%c%02i:%02i:%06.3f %02i:%02i:%05.2f" % (signalt, alth, altm, alts, azh, azm, azs))

    """Set value from string returned by RTS2. Both RA and DEC are in degrees,
    separated by space."""
    def set_string_altaz(self,val):
	self.set_altaz(val["alt"],val["az"])

    def get_altaz(self):
       # split on + or -
       try:
           (alt,az) = string.split(self.get_text(),"+")
	   sign = 1
       except ValueError:
           try:
	       (ra,dec) = string.split(self.get_text(),"-")
	       sign = -1
	   except ValueError:
	       msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format="Cannot parse RADEC string " + self.get_text())
	       msgbox.run()
	       msgbox.hide()
	       return
       return (from_hms(alt), sign * from_hms(dec))

