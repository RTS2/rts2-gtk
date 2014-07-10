#!/usr/bin/python

import gtk
import pyfits
import numpy

w  = gtk.Window()
w.set_title('Test image')

f = pyfits.open('20120214011559-438-RA.fits')
# rescale to 0-255

d=f[0].data

s=''
mn=d.min()
scale = float(d.max() - mn)/255.0
for x in d:
	for y in x:
		vi = int((y - mn) * scale)
		if vi > 256:
			vi = 255
		v = chr(vi)
		s += v + v + v

print d.shape[0],d.shape[1],len(s)

i = gtk.Image()
i.set_from_pixbuf(gtk.gdk.pixbuf_new_from_data(s, gtk.gdk.COLORSPACE_RGB, False, 8, d.shape[0], d.shape[1], d.shape[0]*3))

w.add(i)
w.show_all()
w.connect('destroy',gtk.main_quit)

gtk.main()
