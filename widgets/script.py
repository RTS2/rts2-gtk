#!/usr/bin/env python
# Script editor and display
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
#
# This Python script needs lxml module to parse XML - available in python-lxml package

import gtk
import gettext
import gobject
import login
import targets
import string
import sys
import rts2.rtsapi

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class Element:
	def __init__(self,label):
		self.l = gtk.Label(label)
		self.l.set_alignment(0,0.5)

	def attach(self,table,row,xoff):
		if xoff > 0:
			hb = gtk.HBox()
			hb.pack_start(gtk.Label('         '*xoff),False,False)
			hb.pack_end(self.l,True,True)
			table.attach(hb,0,1,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		else:
			table.attach(self.l,0,1,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		return 1

class Exposure(Element):
	"""Element to start exposure."""
	def __init__(self,dark=False):
		self.dark = dark
		if self.dark:
			Element.__init__(self,_('Dark'))
		else:
			Element.__init__(self,_('Exposure'))
		self.duration = gtk.SpinButton(gtk.Adjustment(1,0,86400,1,10),digits=3)

	def attach(self,table,row,xoff):
		table.attach(self.duration,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK)
		return Element.attach(self,table,row,xoff)
	
	def get_script(self):
		if self.dark:
			return 'D {0}'.format(self.duration.get_value())
		return 'E {0}'.format(self.duration.get_value())
	
	def load_json(self,je):
		self.duration.set_value(je['duration'])

class Acquire(Element):
	def __init__(self):
		Element.__init__(self,_('Acquire'))
		self.precision = gtk.SpinButton(gtk.Adjustment(0,0,60,10),digits=1)
		self.duration = gtk.SpinButton(gtk.Adjustment(1,0,86400,1,10),digits=3)

		# pack it all together
		self.hb = gtk.HBox()
		self.hb.pack_start(gtk.Label(_('precision')),False,False)
		self.hb.pack_start(self.precision,False,False)
		self.hb.pack_start(gtk.Label(_('arcsec')),False,False)
		self.hb.pack_start(gtk.Label('   '),False,False)
		self.hb.pack_start(gtk.Label(_('exposure duration')),False,False)
		self.hb.pack_start(self.duration,False,False)
		self.hb.pack_start(gtk.Label(_('s')),False,False)

	def attach(self,table,row,xoff):
		table.attach(self.hb,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		return Element.attach(self,table,row,xoff)

	def get_script(self):
		return 'A {0:.10f} {1}'.format(self.precision.get_value()/3600.0, self.duration.get_value())

	def load_json(self,je):
		self.precision.set_value(je['precision']*3600.0)
		self.duration.set_value(je['duration'])

class Filter(Element):
	def __init__(self,camera):
		Element.__init__(self,_('Filter'))

		self.filter = login.getProxy().getSelectionComboEntry(camera,'filter',0)

	def attach(self,table,row,xoff):
		table.attach(self.filter,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		return Element.attach(self,table,row,xoff)

	def get_script(self):
		return 'filter={0}'.format(self.filter.child.get_text())

	def load_json(self,je):
		self.filter.child.set_text(je['operands'])

def find_combo_string(combo,s):
	i = 0
	m = combo.get_model()
	it = m.get_iter_first()
	while it is not None:
		if m[it][0] == s:
			return i
		i += 1
		it = m.iter_next(it)
	raise KeyError(s)

class Operation:
	def __init__(self,camera):
		self.hb = gtk.HBox()
		self.camera = camera
			
		self.device = gtk.combo_box_new_text()
		for d in login.getProxy().loadJson('/api/devices'):
			self.device.append_text(d)
		self.device.connect('changed',self.device_changed)
		self.hb.pack_start(self.device,False,False)
		self.hb.pack_start(gtk.Label('.'),False,False)

		self.name = gtk.combo_box_new_text()
		self.name.connect('changed',self.name_changed)
		self.hb.pack_start(self.name,False,True)

		self.opbox = gtk.HBox()

		self.op = None
		self.operands = None

	def attach(self,table,row,xoff):
		table.attach(self.hb,0,1,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		table.attach(self.opbox,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		return 1
	
	def device_changed(self,b):
		m = gtk.ListStore(str)
		d = login.getProxy().getDevice(self.device.get_active_text())
		for n in d.keys():
			if (d[n][0] & rts2.json.RTS2_VALUE_WRITABLE) and n != 'filter':
				m.append([n])
		self.name.set_model(m)
		self.name.set_active(0)

	def name_changed(self,b):
		d = self.device.get_active_text()
		n = self.name.get_active_text()
		self.vf = login.getProxy().getVariable(d,n)[0]
		self.vb = rts2.json.RTS2_VALUE_BASETYPE & self.vf
		if self.operands:
			self.opbox.remove(self.operands)

		if self.vb == rts2.json.RTS2_VALUE_SELECTION:
			self.operands = login.getProxy().getSelectionComboEntry(d,n)
			self.operands.set_active(login.getProxy().getValue(d,n))
		elif self.vb == rts2.json.RTS2_VALUE_INTEGER or self.vb == rts2.json.RTS2_VALUE_LONGINT:
			self.operands = gtk.SpinButton(gtk.Adjustment(0,-sys.maxint - 1,sys.maxint,1,10))
			self.operands.set_width_chars(6)
			self.operands.set_value(int(login.getProxy().getValue(d,n)))
		elif self.vb == rts2.json.RTS2_VALUE_DOUBLE or self.vb == rts2.json.RTS2_VALUE_FLOAT:
			self.operands = gtk.SpinButton(gtk.Adjustment(0,-sys.maxint - 1,sys.maxint,1,10),digits=3)
			self.operands.set_width_chars(6)
			self.operands.set_value(float(login.getProxy().getValue(d,n)))
		elif self.vb == rts2.json.RTS2_VALUE_BOOL:
			self.operands = gtk.HBox()
			self.rb_true = gtk.RadioButton(None,'On')
			self.rb_false = gtk.RadioButton(self.rb_true,'Off')
			self.operands.pack_start(self.rb_true)
			self.operands.pack_end(self.rb_false)
			if login.getProxy().getValue(d,n):
				self.rb_true.set_active(True)
			else:
				self.rb_false.set_active(True)
		else:
			self.operands = gtk.Entry()
			self.operands.set_width_chars(6)
			self.operands.set_text(str(login.getProxy().getValue(d,n)))

		if self.vb == rts2.json.RTS2_VALUE_STRING:
			if self.op:
				self.opbox.remove(self.op)
				self.opbox.pack_start(gtk.Label('='),False,False)
				self.op = None
		elif not self.op:
			self.op = gtk.combo_box_new_text()
			self.op.append_text('-=')
			self.op.append_text('=')
			self.op.append_text('+=')
			self.op.set_active(1)
			self.opbox.pack_start(self.op,False,False)

		self.opbox.pack_end(self.operands,True,True)
		self.opbox.show_all()
			
	def get_script(self):
		operands = None
		if self.vb == rts2.json.RTS2_VALUE_SELECTION:
			operands = self.operands.child.get_text()
		elif self.vb == rts2.json.RTS2_VALUE_INTEGER or self.vb == rts2.json.RTS2_VALUE_LONGINT:
			operands = int(self.operands.get_value())
		elif self.vb == rts2.json.RTS2_VALUE_DOUBLE or self.vb == rts2.json.RTS2_VALUE_FLOAT:
			operands = self.operands.get_value()
		elif self.vb == rts2.json.RTS2_VALUE_BOOL:
			if self.rb_true.get_active():
				operands = '1'
			else:
				operands = '0'
		else:
			operands = self.operands.get_text()

		op = '='
		if not(self.vb == rts2.json.RTS2_VALUE_STRING):
			op = ['+=','=','-='][self.op.get_active()]

		if self.device.get_active_text() == self.camera:
			return '{0}{1}{2}'.format(self.name.get_active_text(),op,operands)
		return '{0}.{1}{2}{3}'.format(self.device.get_active_text(),self.name.get_active_text(),op,operands)
	
	def load_json(self,je):
		self.device.set_active(find_combo_string(self.device,je['device']))
		self.name.set_active(find_combo_string(self.name,je['name']))
		self.name_changed(self.name)

		if self.vb == rts2.json.RTS2_VALUE_SELECTION:
			try:
				self.operands.set_active(int(je['operands']))
			except ValueError,er:
				try:
					self.operands.set_active(find_combo_string(self.operands,je['operands']))
				except KeyError,ke:
					self.operands.child.set_text(je['operands'])
		elif self.vb == rts2.json.RTS2_VALUE_INTEGER or self.vb == rts2.json.RTS2_VALUE_LONGINT:
			self.operands.set_value(int(je['operands']))
		elif self.vb == rts2.json.RTS2_VALUE_DOUBLE or self.vb == rts2.json.RTS2_VALUE_FLOAT:
			self.operands.set_value(float(je['operands']))
		elif self.vb == rts2.json.RTS2_VALUE_BOOL:
			if je['operands'] in ['1','true','on','ON']:
				self.rb_true.set_active(True)
			else:
				self.rb_false.set_active(True)
		else:
			self.operands.set_text(je['operands'])

		if not (self.vb == rts2.json.RTS2_VALUE_STRING):
			if je['cmd'] == '-':
				self.op.set_active(0)
			elif je['cmd'] == '=':
				self.op.set_active(1)
			elif je['cmd'] == '+':
				self.op.set_active(2)

class TargetTempDisable(Element):
	def __init__(self):
		Element.__init__(self,_('Disable target for'))
		self.duration = gtk.SpinButton(gtk.Adjustment(1,0,86400000,1,10),digits=3)

	def attach(self,table,row,xoff):
		table.attach(self.duration,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK)
		return Element.attach(self,table,row,xoff)

	def get_script(self):
		return 'tempdisable {0}'.format(self.duration.get_value())
	
	def load_json(self,je):
		self.duration.set_value(je['duration'])

class Execution(Element):
	def __init__(self):
		Element.__init__(self,_('Execute'))

		self.path = gtk.Entry()

	def attach(self,table,row,xoff):
		table.attach(self.path,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		return Element.attach(self,table,row,xoff)

	def get_script(self):
		return 'exe {0}'.format(self.path.get_text())

	def load_json(self,je):
		self.path.set_text(je['path'])

class Sleep(Element):
	def __init__(self):
		Element.__init__(self,_('Sleep'))
		self.sleeptime = gtk.SpinButton(gtk.Adjustment(1,0,86400,1,10),digits=0)
	
	def attach(self,table,row,xoff):
		table.attach(self.sleeptime,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK)
		return Element.attach(self,table,row,xoff)
	
	def get_script(self):
		return 'sleep {0}'.format(self.sleeptime.get_value())
	
	def load_json(self,je):
		self.sleeptime.set_value(je['seconds'])

class ScriptBlock(gobject.GObject):
	"""Holder for commands inside block."""
	def __init__(self,camera=None):
		gobject.GObject.__init__(self)

		self.entries = []
		self.table = None
		self.xoff = 0

		self.camera = camera

	def attach(self,table,row,xoff):
		self.table = table
		self.row = row
		self.xoff = xoff

		for e in self.entries:
			self.add_buttons(self.row,e)
			self.row += e.attach(table,self.row,xoff)
		return self.row

	def stack_block(self,b):
		pass

	def add_entry(self,w):
		self.entries.append(w)

	def delete_entry(self,b,e):
		self.entries.remove(e)
		self.emit('script-changed')

	def clear(self,bc=None):
		if self.table:
			self.table.foreach(self.table.remove)
		self.entries = []
		self.row = 0

	def get_script(self):
		return string.join(map(lambda x:x.get_script(),self.entries),' ')

	def add_buttons(self,row,e):
		db = gtk.Button()
		db.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE,gtk.ICON_SIZE_MENU))
		db.connect('clicked',self.delete_entry,e)
		self.table.attach(db,2,3,row,row+1,gtk.FILL|gtk.SHRINK,0)

	def load_json(self,script):
		for x in script:
			w = None
			if not x.has_key('cmd'):
				continue
			if x['cmd'] == 'E':
				w = Exposure(False)
			elif x['cmd'] == 'D':
				w = Exposure(True)
			elif x['cmd'] == 'A':
				w = Acquire()
			elif x['cmd'] == '=':
				if x['name'] == 'filter' and x['device'] == self.camera:
					w = Filter(x['device'])
				else:
					w = Operation(self.camera)
			elif x['cmd'] == '+' or x['cmd'] == '-':
				w = Operation(self.camera)
			elif x['cmd'] == 'tempdisable':
				w = TargetTempDisable()
			elif x['cmd'] == 'exe':
				w = Execution()
			elif x['cmd'] == 'sleep':
				w = Sleep()
			elif x['cmd'] == 'for':
				w = BlockFor(self.camera)
				w.connect('script-changed',lambda e:self.emit('script-changed'))

			# add extra rows from possible block..
			w.load_json(x)

			self.entries.append(w)

	def set_target(self,target,camera):
		self.clear()

		self.target = target
		self.camera = camera

		script = login.getProxy().loadJson('/api/script',{'cn':camera,'id':target})
		self.load_json(script)
		self.attach(self.table,0,0)

	def set_script(self):
		if self.target:
			login.getProxy().loadJson('/api/change_script',{'id':self.target,'c':self.camera,'s':self.get_script()})

class MainBlock(ScriptBlock):
	def __init__(self):
		ScriptBlock.__init__(self)

		# stack for blocks embedded into current block
		self.blocks = []

	def get_xoff(self):
		return len(self.blocks)

	def action(self,ba,action):
		w = None
		if action == ScriptEditor.ACTION_EXPOSURE:
			w = Exposure(False)
		elif action == ScriptEditor.ACTION_DARK:
			w = Exposure(True)
		elif action == ScriptEditor.ACTION_FILTER:
			w = Filter(self.camera)
		elif action == ScriptEditor.ACTION_OP:
			w = Operation(self.camera)
		elif action == ScriptEditor.ACTION_EXE:
			w = Execution()
		elif action == ScriptEditor.ACTION_SLEEP:
			w = Sleep()
		elif action == ScriptEditor.ACTION_FOR:
			w = BlockFor(self.camera)
			w.connect('script-changed',lambda e:self.emit('script-changed'))

		w.attach(self.table,self.row,self.get_xoff())

		try:
			self.blocks[-1].add_buttons(self.row,w)
		except IndexError,ie:
			self.add_buttons(self.row,w)

		self.add_entry(w)

		if action == ScriptEditor.ACTION_FOR:
			self.stack_block(w)

		self.row += 1

	def stack_block(self,b):
		self.blocks.append(b)

	def unstack_block(self):
		self.blocks = self.blocks[:-1]

	def add_entry(self,w):
		try:
			self.blocks[-1].add_entry(w)
		except IndexError,ie:
			ScriptBlock.add_entry(self,w)

	def clear(self,bc=None):
		self.blocks = []

		ScriptBlock.clear(self,bc)


class BlockFor(ScriptBlock):
	def __init__(self,camera):
		ScriptBlock.__init__(self,camera)
		self.l = gtk.Label(_('Repeat'))
		self.l.set_alignment(0,0.5)
		self.count = gtk.SpinButton(gtk.Adjustment(1,1,sys.maxint,1,10))

	def attach(self,table,row,xoff):
		if xoff > 0:
			hb = gtk.HBox()
			hb.pack_start(gtk.Label('         '*xoff),False,False)
			hb.pack_end(self.l,True,True)
			table.attach(hb,0,1,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)
		else:
			table.attach(self.l,0,1,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)

		table.attach(self.count,1,2,row,row+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,0)

		return ScriptBlock.attach(self,table,row+1,xoff+1)

	def get_script(self):
		return 'for {0} {{ {1} }}'.format(self.count.get_value_as_int(),ScriptBlock.get_script(self))

	def load_json(self,je):
		self.count.set_value(je['count'])
		return ScriptBlock.load_json(self,je['block'])

class ScriptEditor(gtk.HBox):

	ACTION_EXPOSURE  = 0
	ACTION_DARK      = 1
	ACTION_FILTER    = 2
	ACTION_OP        = 3
	ACTION_EXE       = 4
	ACTION_SLEEP     = 5
	ACTION_FOR       = 6

	def __init__(self):
		gtk.HBox.__init__(self,spacing=5)

		self.buttons = gtk.VButtonBox()
		self.buttons.set_layout(gtk.BUTTONBOX_START)

		self.table = gtk.Table(1,3)
		self.script = MainBlock()
		self.script.attach(self.table,0,0)

		gscw = gtk.ScrolledWindow()
		gscw.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
		gscw.add_with_viewport(self.table)

		self.pack_start(gscw,True,True)
		self.pack_end(self.buttons,False,False)

		ba = gtk.Button(_('Add command'))
		ba.connect('clicked',self.add_command)
		self.buttons.add(ba)

		self.endloop = gtk.Button(_('End loop'))
		self.endloop.connect('clicked',self.end_loop)
		self.endloop.set_sensitive(False)
		self.buttons.add(self.endloop)

		bc = gtk.Button(_('Clear'))
		bc.connect('clicked',self.script.clear)
		self.buttons.add(bc)

		self.script.connect('script-changed',self.script_changed)

	def add_command(self,ba):
		self.dialog = gtk.Dialog(_('Add new command'),None,gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))

		self.exposure = gtk.Button(_('Exposure'))
		self.exposure.connect('clicked',self.action,self.ACTION_EXPOSURE)
		self.dialog.vbox.add(self.exposure)

		self.dark = gtk.Button(_('Dark'))
		self.dark.connect('clicked',self.action,self.ACTION_DARK)
		self.dialog.vbox.add(self.dark)

		self.filter = gtk.Button(_('Filter'))
		self.filter.connect('clicked',self.action,self.ACTION_FILTER)
		self.dialog.vbox.add(self.filter)

		self.opcmd = gtk.Button(_('Operation'))
		self.opcmd.connect('clicked',self.action,self.ACTION_OP)
		self.dialog.vbox.add(self.opcmd)

		self.exe = gtk.Button(_('Script execution'))
		self.exe.connect('clicked',self.action,self.ACTION_EXE)
		self.dialog.vbox.add(self.exe)

		self.sleep = gtk.Button(_('Sleep'))
		self.sleep.connect('clicked',self.action,self.ACTION_SLEEP)
		self.dialog.vbox.add(self.sleep)

		self.forl = gtk.Button(_('For loop'))
		self.forl.connect('clicked',self.action,self.ACTION_FOR)
		self.dialog.vbox.add(self.forl)

		self.dialog.show_all()

		ret = self.dialog.run()
		self.dialog.destroy()

		self.endloop.set_sensitive(len(self.script.blocks))

	def end_loop(self,ba):
		self.script.unstack_block()
		self.endloop.set_sensitive(len(self.script.blocks))

	def get_script(self):
		return self.script.get_script()

	def script_changed(self,orig):
		self.table.foreach(self.table.remove)
		self.script.attach(self.table,0,0)
		self.show_all()

	def action(self,ba,action):
		self.script.action(ba,action)

		self.show_all()
		self.dialog.response(gtk.RESPONSE_ACCEPT)

class ScriptDialog(gtk.Dialog):
	def __init__(self,title=None,parent=None,flags=0,buttons=None,target=1,camera='C0'):
		gtk.Dialog.__init__(self,title,parent,flags,buttons)
		self.set_geometry_hints(min_width=600,min_height=300)

		self.scripteditor = ScriptEditor()
		self.vbox.add(self.scripteditor)

		self.scripteditor.script.target = target

		self.l = gtk.Label('')
		self.l.set_alignment(0,0.5)
		self.vbox.pack_end(self.l,False,False)

		b = gtk.Button(_('Generate'))
		b.connect('clicked',self.generate)
		self.action_area.add(b)

		b = gtk.Button(_('Set script'))
		b.connect('clicked',self.set_script)
		self.action_area.add(b)

		self.cam = gtk.combo_box_new_text()
		cams = login.getProxy().loadJson('/api/devbytype',{'t':3})

		for x in cams:
			self.cam.append_text(x)

		self.cam.connect('changed',self.select_camera)
		self.cam.set_active(0)
		self.action_area.add(self.cam)

		self.show_all()
	
	def set_target(self,target,camera):
		self.scripteditor.script.set_target(target,camera)
		self.set_title(_('Script for target {0} and camera {1}').format(target,camera))
		self.show_all()

	def generate(self,b):
		self.l.set_text(self.scripteditor.get_script())

	def set_script(self,b):
		self.scripteditor.script.set_script()

	def select_camera(self,b):
		self.set_target(self.scripteditor.script.target,self.cam.get_active_text())

gobject.signal_new('script-changed',ScriptBlock,gobject.SIGNAL_RUN_FIRST,gobject.TYPE_NONE,[])

# test routine
if __name__ == '__main__':
	l = login.Login()
	l.signon()

	d = login.getProxy().hlib.request('GET', login.getProxy().prefix + '/api/script?id=1&cn=C0',None,login.getProxy().headers)
	r = login.getProxy().hlib.getresponse()

	def select_target(b,diag):
		d = targets.SelectDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,buttons=[(gtk.STOCK_OK,1),(gtk.STOCK_CANCEL,0)])
		if d.run() == 1:
			diag.t = d.getSelected(0)[0]
			diag.set_target(diag.t,diag.cam.get_active_text())
			b.set_label('Target {0}'.format(diag.t))

		d.destroy()
	
	diag = ScriptDialog(target=1)

	diag.t = 1

	b = gtk.Button('Target 1')
	b.connect('clicked',select_target,diag)
	diag.action_area.add(b)

	diag.show_all()
	diag.run()
	
