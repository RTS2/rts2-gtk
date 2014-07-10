#!/usr/bin/env python
# COnstraint editor and display
# Copyright (C) 2011 Petr Kubanek, Institute of Physics <kubanek@fzu.cz>
#
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

import gtk
import gettext
import login

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class ConstraintsStore(gtk.ListStore):
	"""Constraints store."""
	def __init__(self):
		gtk.ListStore.__init__(self,str,float,float)

	def load_target(self,id):	
		const = login.getProxy().loadJson('/api/consts',{'id':id})
		for c in const:
			if c == 'maxRepeats':
				self.append([c,float('nan'),const[c]])
			else:
				for interval in const[c]:
					mi,ma = interval
					if mi is None:
						mi = float('nan')
					if ma is None:
						ma = float('nan')
					self.append([c,mi,ma])

class ConstraintsWindow(gtk.ScrolledWindow):
	def __init__(self):
		gtk.ScrolledWindow.__init__(self)
		self.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

		self.data = ConstraintsStore()
		self.tv = gtk.TreeView(self.data)

		tvcolumn = gtk.TreeViewColumn(_('Constraint'))
		self.tv.append_column(tvcolumn)
		cell = gtk.CellRendererText()
		tvcolumn.pack_start(cell,True)
		tvcolumn.set_attributes(cell,text=0)
		tvcolumn.set_sort_column_id(0)

		tvcolumn = gtk.TreeViewColumn(_('Min'))
		self.tv.append_column(tvcolumn)
		cell = gtk.CellRendererSpin()
		tvcolumn.pack_start(cell,True)
		tvcolumn.set_attributes(cell,text=1)
		cell.set_property('editable',True)
		cell.set_property('digits',3)
		cell.set_property('adjustment',gtk.Adjustment(-90,-90,90,1,10))
		cell.connect('edited',self.min_edited)

		tvcolumn = gtk.TreeViewColumn(_('Max'))
		self.tv.append_column(tvcolumn)
		cell = gtk.CellRendererSpin()
		tvcolumn.pack_start(cell,True)
		tvcolumn.set_attributes(cell,text=2)
		cell.set_property('editable',True)
		cell.set_property('digits',3)
		cell.set_property('adjustment',gtk.Adjustment(-90,-90,90,1,10))
		cell.connect('edited',self.max_edited)

		self.tv.set_search_column(0)
		self.tv.set_reorderable(True)

		self.add(self.tv)
		self.show_all()

	def min_edited(self,cellrenderertext,path,new_text):
		self.data[path][1] = float(new_text)

	def max_edited(self,cellrenderertext,path,new_text):
		self.data[path][2] = float(new_text)

class ConstraintsDialog(gtk.Dialog):
	def __init__(self):
		gtk.Dialog.__init__(self)
		self.sw = ConstraintsWindow()
		self.sw.data.load_target(1000)
		self.vbox.pack_start(self.sw)
		self.show_all()

# test routine
if __name__ == '__main__':
	l = login.Login()
	l.signon()

	diag = ConstraintsDialog()
	diag.run()
