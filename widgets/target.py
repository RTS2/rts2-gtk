#!/usr/bin/env python
"""Display target informations in tabs"""
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import gettext
import gobject
import gtk
import jsontable
import login
import script
import constraints
import gtkradec
import targets

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class NameLabel(gtk.Label):
	def __init__(self,str=None):
		gtk.Label.__init__(self,str)
		self.set_alignment(0,0.5)

class TargetBasic(gtk.Table):
	def __init__(self):
		gtk.Table.__init__(self,1,2)

		self.attach(NameLabel(_('Target ID:')),0,1,0,1,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)
		self.idl = NameLabel(id)
		self.attach(self.idl,1,2,0,1,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)
		
		self.attach(NameLabel(_('Target name:')),0,1,1,2,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)
		self.tarname = gtk.Entry()
		self.attach(self.tarname,1,2,1,2,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)

		self.attach(NameLabel(_('Coordinates:')),0,1,2,3,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)
		self.coordinates = gtkradec.RaDec()
		self.attach(self.coordinates,1,2,2,3,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)

		self.attach(NameLabel(_('Description:')),0,1,3,4,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)
		self.desc = gtk.Entry()
		self.attach(self.desc,1,2,3,4,gtk.SHRINK|gtk.EXPAND|gtk.FILL,0)

		gobject.idle_add(self.show_all)

	def set_target(self,id):
		tar = login.getProxy().loadJson('/api/tbyid',{'id':id})['d'][0]

		self.idl.set_text(str(id))
		self.tarname.set_text(tar[1])
		self.coordinates.set_radec(tar[2],tar[3])
		self.desc.set_text(tar[4])

	def save_target(self):
		(ra,dec) = self.coordinates.get_radec()
		return login.getProxy().loadJson('/api/update_target',{'id':int(self.idl.get_text()),'tn':self.tarname.get_text(),'ra':ra,'dec':dec,'desc':self.desc.get_text()})

class TargetObservation(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)

		self.obs = None

		gobject.idle_add(self.show_all)

	def set_target(self,id):
		if self.obs:
			self.remove(self.obs)
		self.obs = jsontable.JsonTable('/api/obytid',{'id':id})
		self.pack_start(self.obs,True,True)

		gobject.idle_add(self.show_all)

class TargetNotebook(gtk.Notebook):
	def __init__(self,id=None):
		gtk.Notebook.__init__(self)

		self.basic = TargetBasic()
		self.append_page(self.basic,gtk.Label(_('Target')))
		
		self.alt = targets.TargetsConstraintBox()
		self.append_page(self.alt,gtk.Label(_('Altitude')))

		self.observations = TargetObservation()
		self.append_page(self.observations,gtk.Label(_('Observations')))

		self.cameras = login.getProxy().loadJson('/api/devbytype',{'t':3})
		self.cameras.reverse()
		self.camid = []
		self.scripts = []

		if id:
			self.set_target(id)

		gobject.idle_add(self.show_all)

	def set_target(self,id):
		self.basic.set_target(id)
		for x in self.camid:
			self.remove_page(x)
		self.camid = []
		self.scripts = []
		for x in self.cameras:
			se = script.ScriptEditor()
			se.script.set_target(id,x)
			self.camid.append(self.insert_page(se,gtk.Label(x),1))
			self.scripts.append(se)
		
		self.alt.clear_targets()
		self.alt.add(id,'Active')

		self.observations.set_target(id)

		self.id = id

		gobject.idle_add(self.show_all)
	
	def save_target(self):
		self.basic.save_target()
		for x in self.scripts:
			x.script.set_script()

class TargetDialog(gtk.Dialog):

	def __init__(self,id):
		gtk.Dialog.__init__(self,title=_('Target'))

		self.set_geometry_hints(min_width=800, min_height=400)

		gobject.idle_add(self.show_all)

		self.tarnb = TargetNotebook(id)
		self.set_title(_('Target {0} at {1}').format(self.tarnb.basic.tarname.get_text(), self.tarnb.basic.coordinates.get_text()))

		self.vbox.add(self.tarnb)

		b = gtk.Button(stock=gtk.STOCK_APPLY)
		b.connect('clicked', self.apply)
		self.action_area.add(b)

		b = gtk.Button(stock=gtk.STOCK_CANCEL)
		b.connect('clicked', lambda x:self.hide())
		self.action_area.add(b)

		gobject.idle_add(self.show_all)

	def apply(self, b):
		self.tarnb.save_target()
		self.hide()

if __name__ == '__main__':
  	l = login.Login()
	l.signon()

	notebook = TargetDialog(1000)
	notebook.connect('destroy',gtk.main_quit)
	notebook.run()
