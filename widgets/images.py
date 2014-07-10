#!/usr/bin/env python
"""Load and display images. Allows image manipulation (load it to DS9,..)"""
#
# Petr Kubanek <petr@kubanek.net>

import ds9
import jsontable
import login

import gettext
t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

l = login.Login()
l.signon()

db = jsontable.JsonSelectDialog('/api/ibyoid',{'oid',864},buttons=[(_('DS9'),1),(_('Close'),2)])

def responded(d,resp,db):
	if resp == 1:
		for x in db.getSelected(0):
			print x
	else:
		db.hine()
		db = None

db.connect('response',responded,db)
db.show()
