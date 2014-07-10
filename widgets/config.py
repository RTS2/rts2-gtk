#!/usr/bin/python

import gtk
import ConfigParser
import gtkradec

class ConfigWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		self.set_title('RTS2 configuration')

		table = gtk.Table(2,4)

		self.lat = gtkradec.Dec()
		table.attach(self.lat,1,2,0,1)

		self.lon = gtkradec.Dec()
		table.attach(self.lon,1,2,1,2)

		bb = gtk.HButtonBox()

		save = gtk.Button('Save')
		save.connect('clicked',self.save)
		bb.add(save)

		vb = gtk.VBox()
		vb.pack_start(table,False)
		vb.pack_end(bb,False)

		self.add(vb)

		self.load()

		self.show_all()

	def load(self):
		self.co = ConfigParser.ConfigParser()
		self.co.read('/etc/rts2/rts2.ini')

		self.lat.set_dec(self.co.getfloat('observatory','latitude'))
		self.lon.set_dec(self.co.getfloat('observatory','longitude'))

	
	def save(self,b):	
		cf = open('/tmp/rts2.ini','w')

		self.co.set('observatory','latitude',self.lat.get_dec())
		self.co.set('observatory','longitude',self.lon.get_dec())
		self.co.write(cf)
		cf.close()

if __name__ == '__main__':
  	c = ConfigWindow()
	c.connect('destroy',gtk.main_quit)
	gtk.main()
