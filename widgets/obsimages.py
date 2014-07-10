#!/usr/bin/env python
"""Load and display night images"""
#
# Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import login
import jsontable
import gtk

global DS9_AVAILABLE
DS9_AVAILABLE=False

try:
	import ds9
	DS9_AVAILABLE=True
except ImportError,ie:
	pass

import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class ImageDialog(jsontable.JsonSelectDialog):
	def __init__(self,oid):
		jsontable.JsonSelectDialog.__init__(self,'/api/ibyoid',{'oid':oid},buttons=[(_('Run DS9'),1),(_('Update'),2),(_('Done'),3)],selmode=gtk.SELECTION_MULTIPLE)

		self.oid = oid
		self.set_geometry_hints(min_width=500,min_height=400)
		self.set_title(_('Observation {0}').format(self.oid))

		self.connect('response',self.responded)

	def responded(self,d,resp):
		if resp == 1:
			self.runds9()
		elif resp == 2:
			self.js.reload('/api/ibyoid',{'oid':self.oid})
		else:
			self.hide()

	def runds9(self):
		if not DS9_AVAILABLE:
			return
		d = ds9.ds9('runtime')
		d.set('frame delete all')
		first = True
		for x in self.getSelected(0):
			d.set('frame new')
			d.set('file mosaicimage iraf {0}'.format(x))
			d.set('scale zscale')	
			d.set('zoom to fit')	
		d.set('tile mode grid')	
		d.set('tile')
		d.set('zoom to fit')
		d.set('match frames physical')
	
if __name__ == '__main__':
  	l = login.Login()
	l.signon()
	
	d = ImageDialog(852)
	d.connect('destroy',gtk.main_quit)
	gtk.main()
