#!/usr/bin/env python
"""Load and display targets."""
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
# Petr Kubanek <petr@kubanek.net>

import copy
import gobject
import gtk
import gettext
import threading
import jsontable
import math
import login
import radec
import time
import re
import houraxis

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class TargetLabel(gtk.EventBox):
	"""Simple target label."""

	def __init__(self, id, start=time.time(), colorBellow=True, colorViolated=True, invalidText=None, withStartTime=False):
		gtk.EventBox.__init__(self)
		self.label = gtk.Label()
		self.label.set_alignment(0,0.5)
		self.basecolor = self.style.bg[gtk.STATE_NORMAL]
		self.id = id
		self.start = start
		self.target_name = None
		self.colorBellow = colorBellow
		self.colorViolated = colorViolated
		self.invalidText = invalidText
		self.withStartTime = withStartTime
		self.add(self.label)

	def set_id(self, id, start=None):
		self.id = id
		if start is None:
			self.set_start(time.time())
		else:
			self.set_start(start)
		self.reload()

	def set_start(self, start):
		self.start = start	

	def reload(self):
		"""Load target"""
		if self.id is None:
			if self.invalidText:
				self.label.set_markup(self.invalidText)
			else:	
				self.label.set_markup('<b>{0}</b> not valid'.format(self.id))
			return
		try:
			params = {'id':self.id, 'e':'1'}
			if self.start:
				params['from'] = int(self.start)
			self.data = login.getProxy().loadJson('/api/tbyid', params)['d'][0]
		except Exception,ex:
			import traceback
			traceback.print_exc(ex)
			self.label.set_markup('<b>{0}</b> not loaded'.format(self.id))
			self.data = [self.id, 'does not exist', None, None, 360.0, 0, [], [], ['all'], None, False]

		self.target_name=self.data[1]
		if self.withStartTime and self.start:
			self.label.set_markup('<i>{0}</i> <b>{1}</b> <i>({2})</i> {3} {4}'.format(time.strftime('%H:%M:%S', time.localtime(self.start)), self.target_name, self.id, radec.ra_string(self.data[2]), radec.dec_string(self.data[3])))
		else:
			self.label.set_markup('<b>{0}</b> <i>({1})</i> {2} {3}'.format(self.target_name,self.id, radec.ra_string(self.data[2]), radec.dec_string(self.data[3])))
		self.violated = self.data[8]
		if (self.colorViolated and len(self.violated) > 0) or (self.colorBellow and self.data[10] == False):
			self.color = gtk.gdk.Color('magenta')
		else:
			self.color = self.basecolor
		self.modify_bg(gtk.STATE_NORMAL,self.color)

	def setColorViolated(self,colorViolated):
		self.colorViolated = colorViolated

	def duration(self):
		return self.data[5]

class TargetsList(gtk.ListStore):
	def __init__(self):
		# id, name, RA, DEC, ALT, AZ
		gtk.ListStore.__init__(self,str,float,float,float,float,'gboolean')

		res = login.getProxy().loadJson('/api/tbytype',{'t':'O'})
		for x in res:
			self.append([x['name'],x['ra'],x['dec'],x['alt'],x['az'],x['enabled']])


class Targets(gtk.ScrolledWindow):

	def __init__(self):
		gtk.ScrolledWindow.__init__(self)
		self.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

		self.targets = TargetsList()
		self.sm = gtk.TreeModelSort(self.targets)
		self.tv = gtk.TreeView(self.sm)
		self.tv.set_rules_hint(True)

		colHeads = [_('Name'), _('RA'), _('DEC'), _('Altitude'), _('Azimuth'),_('Enabled')]
		colRenders = [None, self.renderRa, self.renderDec, self.renderAlt, self.renderAz, None]

		for i in range(0,len(colHeads)):
			col = gtk.TreeViewColumn(colHeads[i])
			col.set_sort_column_id(i)
			col.set_expand(False)
			if i==5:
				cel = gtk.CellRendererToggle()
				col.pack_start(cel)
				col.set_attributes(cel,active=i)
			else:
				cel = gtk.CellRendererText()
				col.pack_start(cel)
				if colRenders[i] is not None:
					col.set_cell_data_func(cel,colRenders[i])  
				else:	
					col.set_attributes(cel,text=i)

			self.tv.append_column(col)

		self.tv.set_reorderable(True)

		self.add(self.tv)

	def renderRa(self,column,cell,model,iter):
		cell.set_property('text', radec.ra_string(model.get_value(iter,1)))

	def renderDec(self,column,cell,model,iter):
		cell.set_property('text', radec.dec_string(model.get_value(iter,2)))

	def renderAlt(self,column,cell,model,iter):
		cell.set_property('text', radec.dec_string(model.get_value(iter,3)))

	def renderAz(self,column,cell,model,iter):
		cell.set_property('text', radec.dec_string(model.get_value(iter,4)))

class TargetGraph:
	"""Area to hold various target graphs."""
	def __init__(self, id, fr, to, color):
		self.id = id
		self.visible = True
		self.cnst_alt_v = None
		self.cnst_time_v = None
		self.visible_constraints = []

		self.fr = fr
		self.to = to
		self.color = color

		if self.fr > self.to:
			self.fr = int(time.time())
			self.to = self.fr + 86400

	def update(self,visible,color):
		self.visible = visible
		self.color = color

	def alt_to_y(self,alt):
		return self.alt_scale * (self.alt_from - alt)

	def time_to_x(self,t):
		return self.time_scale * (t - self.fr)

	def get_altitude_constraints_v(self):
		if self.cnst_alt_v is None:
			self.cnst_alt_v = login.getProxy().loadJson('/api/cnst_alt_v',{'id':self.id})['altitudes']
		return self.cnst_alt_v

	def get_time_constraints_v(self,rect):
		if self.cnst_time_v is None:
		  	self.cnst_time_v = login.getProxy().loadJson('/api/cnst_time_v', {'id':self.id, 'from':self.fr, 'to':self.to, 'steps':rect.width})['constraints']
		return self.cnst_time_v

	def draw_alt_constraints(self,context,rect):
		context.set_source_rgba(1, 0, 0, 0.30)
		self.get_altitude_constraints_v()
		for c in self.cnst_alt_v:
			if c in self.visible_constraints:
				for (yu,yl) in self.cnst_alt_v[c]:
					yy = self.alt_to_y(yu)
					context.rectangle(0,yy,rect.width,self.alt_to_y(yl)-yy)
		context.fill()

	def draw_time_constraints(self, context, rect):
		context.set_source_rgba(0, 0, 1, 0.30)
		self.get_time_constraints_v(rect)
		for c in self.cnst_time_v:
			if c in self.visible_constraints:
				for (xl,xu) in self.cnst_time_v[c]:
					context.rectangle(self.time_to_x(xl), 0, self.time_to_x(xu), rect.height)
		context.fill()

	def update_data(self,rect):
		self.alts = login.getProxy().loadJson('/api/taltitudes',{'id':self.id, 'from':self.fr, 'to':self.to, 'steps':rect.width})
	
	def draw_target(self, context, rect, h):
		if not(self.visible):
			return

		self.alt_from = 90.0
		self.alt_scale = rect.height / 180.0

		self.time_scale = rect.width / float(self.to - self.fr)

		context.set_source_rgba(self.color[0], self.color[1], self.color[2], 1.0)
		context.set_line_width(1)

		context.move_to(0, self.alt_to_y(self.alts[0]))
		x = 1
		for y in self.alts[1:]:
			context.line_to(x,self.alt_to_y(y))
			x += 1
		context.stroke()

	def set_visible_constraint(self,cn,cs):
		if cs:
			if not (cn in self.visible_constraints):
				self.visible_constraints.append(cn)
		else:
			try:
				self.visible_constraints.remove(cn)
			except ValueError,ve:
				pass

class TargetColors(gtk.VBox):

	def __init__(self):
		gtk.VBox.__init__(self)

		self.tids = []
		self.last_color = [65535,32767,0]
		self.table = gtk.Table(1,5)
		self.actions = gtk.HBox()

		bb = gtk.Button()
		bb.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD,gtk.ICON_SIZE_MENU))
		bb.connect('clicked',self.add_targets)
		self.actions.add(bb)

		bb = gtk.Button()
		bb.set_image(gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_MENU))
		bb.connect('clicked',self.clear_targets)
		self.actions.add(bb)

		self.pack_start(self.table,True,True)
		self.pack_end(self.actions,False,False)

		gobject.idle_add(self.show_all)
	
	def reload(self):
		self.table.foreach(self.table.remove)

		r = 0
		rb = None
		for x in self.tids:
			rb = gtk.RadioButton(group=rb)
			rb.connect('toggled',self.target_active,x)
			self.table.attach(rb,0,1,r,r+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK,xpadding=5)

			cb = gtk.CheckButton()
			cb.connect('toggled',self.target_visible,x)
			cb.set_active(x[0])
			self.table.attach(cb,1,2,r,r+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK,xpadding=5)

			l = gtk.Label(x[1])
			l.set_alignment(0,0.5)
			self.table.attach(l,2,3,r,r+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK,xpadding=5)

			l = gtk.Label(x[2])
			l.set_alignment(0,0.5)
			self.table.attach(l,3,4,r,r+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK,xpadding=5)

			b = gtk.HBox()

			cols = map(lambda x:int(x*65535),x[3])

			bb = gtk.ColorButton(gtk.gdk.Color(*cols))
			bb.connect('color-set',self.set_color,x)
			b.add (bb)

			bb = gtk.Button()
			bb.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE,gtk.ICON_SIZE_MENU))
			bb.connect('clicked',self.delete_tid,x)
			b.add(bb)

			self.table.attach(b,4,5,r,r+1,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.SHRINK)

			r += 1
		gobject.idle_add(self.show_all)
	
	def target_visible(self,cb,x):
		x[0] = cb.get_active()
		self.emit('target-changed',self.tids)

	def target_active(self,cb,x):
		self.emit('target-active',x[1])

	def add(self,tid,tname):
		x = [True,tid,tname,map(lambda x:x / 65535.0, self.last_color)]
		self.tids.append(x)

		for ci in range(0,len(self.last_color)):
			self.last_color[ci] = (self.last_color[ci] + [6553,9830,19660][ci]) % 65535

	def delete_tid(self,b,tid):
		self.tids.remove(tid)
		self.reload()
		self.emit('target-changed',self.tids)

	def set_color(self,b,x):
		c = b.get_color()
		x[3] = (c.red / 65535.0,c.green / 65535.0,c.blue / 65535.0)
		self.emit('target-changed',self.tids)

	def add_targets(self,b):
		d = SelectDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,buttons=[(gtk.STOCK_OK,1),(gtk.STOCK_CANCEL,0)],selmode=gtk.SELECTION_MULTIPLE)
		if d.run() == 1:
			i = 0
			for x in d.getSelected(0):
				self.add(d.getSelected(0)[i],d.getSelected(1)[i])
				i += 1
			self.reload()
			self.emit('target-changed',self.tids)
		d.destroy()

	def clear_targets(self,b):
		self.tids = []
		self.reload()
		self.emit('target-changed',self.tids)
			
class TargetGraphTable(gtk.Table):
	"""Full altitude graph, with altitude axis and time axis."""
	def __init__(self):
		gtk.Table.__init__(self,2,2,False)
		
		self.tg = gtk.DrawingArea()

		self.fr = int(login.getProxy().getValue('centrald', 'sun_set', refresh_not_found=True) - 1800)
		self.to = int(login.getProxy().getValue('centrald', 'sun_rise') + 1800)
		if self.fr > self.to:
			self.fr -= 86400

		self.targets = []
		self.active_target = None

		self.update_lock = threading.Lock()
		self.data_rect = None
		self.sun_alts = []

		self.tg.set_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
		self.tg.connect('expose-event',self.expose)
		self.attach(self.tg,1,2,0,1,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL)

		def motion_notify(ruler,event):
			return ruler.emit('motion-notify-event',event)

		self.vr = gtk.VRuler()
		self.vr.set_metric(gtk.PIXELS)
		self.vr.set_range(90,-90,10,90)
		self.tg.connect_object('motion-notify-event',motion_notify,self.vr)
		self.attach(self.vr,0,1,0,1,gtk.FILL,gtk.EXPAND|gtk.SHRINK|gtk.FILL)

		self.hr = houraxis.HourAxis(self.fr,self.to - self.fr)
		self.tg.connect_object('motion-notify-event',motion_notify,self.hr)
		self.attach(self.hr,1,2,1,2,gtk.EXPAND|gtk.SHRINK|gtk.FILL,gtk.FILL)

		self.rect = self.get_allocation()

		threading.Thread(target=self.update).start()

	def find_target(self,id):
		for x in self.targets:
			if x.id == id:
				return x
		raise IndexError('cannot find target with ID {0}'.format(id))

	def target_changed(self,b,ts):
		# update target set
		for x in ts:
			try:
				tar = self.find_target(x[1])
				tar.update(x[0],x[3])
			except IndexError,ie:
				self.targets.append(TargetGraph(x[1], self.fr, self.to, x[3]))

		ids = map(lambda x:x[1],ts)
		for x in self.targets:
			if not (x.id in ids):
				if x == self.active_target:
					self.active_target = None
				self.targets.remove(x)

		try:
			if self.active_target is None:
				self.active_target = self.targets[0]
		except IndexError,ie:
			pass

	def target_active(self,id):
		try:
			self.active_target = self.find_target(id)
		except IndexError,ie:
			self.active_target = None

	def update(self):
		"""Update data for given rect size. Run in thread for expose event"""
		try:
			self.update_lock.acquire()

			self.dh = float(login.getProxy().getValue('centrald','day_horizon'))
			self.nh = float(login.getProxy().getValue('centrald','night_horizon'))

			self.sun_alts = login.getProxy().loadJson('/api/sunalt',{'from':self.fr,'to':self.to,'step':self.rect.width})

			try:
				self.active_target.get_altitude_constraints_v()
				self.active_target.get_time_constraints_v(self.rect)
			except AttributeError,ae:
				pass

			for tar in self.targets:
				tar.update_data(self.rect)

			self.data_rect = self.rect
		finally:
			self.update_lock.release()
			gobject.idle_add(self.queue_draw)

	def expose(self,widget,event):
		self.context = widget.window.cairo_create()
		self.context.rectangle(event.area.x,event.area.y,event.area.width,event.area.height)
		self.context.clip()

		self.rect = self.get_allocation()

		if self.data_rect == self.rect and self.update_lock.acquire(False):
			try:
				self.draw_sun()
				self.draw()
			finally:
				self.update_lock.release()
		else:
			# refresh data
			threading.Thread(target=self.update).start()

	def draw(self):
		h = self.rect.height / 180.0

		for tar in self.targets:
			tar.draw_target(self.context,self.rect, h)

		try:
			self.active_target.draw_alt_constraints(self.context, self.rect)
			self.active_target.draw_time_constraints(self.context, self.rect)
		except AttributeError,ae:
			pass

		self.context.set_source_rgba(0, 0, 0, 0.8)
		self.context.set_line_width(1)
		self.context.move_to(0, h * 90)
		self.context.line_to(self.rect.width, h * 90)
		self.context.stroke()

		self.draw_currenttime(self.context, self.rect)

		return False

	def draw_sun(self):
		x = 0
		p = None
		for y in self.sun_alts:
			sa = y[0]
			if sa > self.dh:
				x += 1
				continue
			elif sa < self.nh:
				p = 0.0
			else:
				p = (sa - self.nh) / (self.dh - self.nh)

			self.context.set_source_rgba (p, p, p, 0.5)
			self.context.move_to(x,0)
			self.context.line_to(x,self.rect.height)
			self.context.stroke()
			x += 1

	def draw_currenttime(self, context, rect):
		context.set_source_rgba(0, 0.5, 0.5, 1.0)
		context.set_line_width(2)

		x = rect.width / float(self.to - self.fr) * (time.time () - self.fr)

		context.move_to(x, 0)
		context.line_to(x, rect.height)
		context.stroke()

	def set_visible_constraint(self,o):
		for x in o.model:
			self.active_target.set_visible_constraint(x[1],x[0])
		self.tg.queue_draw()

class ConstraintsDisplay(gtk.TreeView):
	def __init__(self):
		self.model = gtk.ListStore(gobject.TYPE_BOOLEAN,str)
		self.sm = gtk.TreeModelSort(self.model)

		gtk.TreeView.__init__(self,self.sm)

		col = gtk.TreeViewColumn(_('Show'))
		col.set_sort_column_id(0)
		col.set_expand(False)
		cel = gtk.CellRendererToggle()
		cel.set_property('activatable',True)
		cel.connect('toggled',self.show_toggled_cb)
		col.pack_start(cel)
		col.set_attributes(cel,active=0)
		self.append_column(col)

		col = gtk.TreeViewColumn(_('Constraint name'))
		col.set_sort_column_id(1)
		col.set_expand(True)
		cel = gtk.CellRendererText()
		col.pack_start(cel)
		col.set_attributes(cel,text=1)
		self.append_column(col)

		self.set_reorderable(True)

	def set_constraints(self,names):
		self.model.clear()

		for x in names:
			self.model.append([True,x])

	def show_toggled_cb(self,cell,path):
		self.model[path][0] = not self.model[path][0]
		self.emit('constraint-changed')

class TargetsConstraintBox(gtk.HBox):
	def __init__(self):
		gtk.HBox.__init__(self)

		self.tt = TargetGraphTable()
		self.ct = ConstraintsDisplay()

		self.ct.connect('constraint-changed',self.constraint_changed)

		self.vbox_tg = gtk.VBox()
		self.tids = TargetColors()

		self.pack_start(self.vbox_tg,True,True)
		self.pack_end(self.tids,False,False)

		self.tids.connect('target-changed',self.target_changed)
		self.tids.connect('target-active',self.target_active)
		self.vbox_tg.pack_start(self.tt,True,True)

		self.vbox_tg.pack_start(self.ct,False,False)

	def add(self,tid,tname):
		self.tids.add(tid,tname)
		self.tids.reload()
	
	def clear_targets(self):
		self.tids.clear_targets(None)

	def target_changed(self,b,ts):
		self.tt.target_changed(b,ts)

		all_constraints = []
		if self.tt.active_target:
			all_constraints = self.tt.active_target.get_altitude_constraints_v().keys()
			if self.tt.rect:
				all_constraints.extend(self.tt.active_target.get_time_constraints_v(self.tt.rect).keys())
			self.ct.set_constraints(all_constraints)
			self.tt.set_visible_constraint(self.ct)

		self.tt.tg.queue_draw()

	def target_active(self,b,id):
		self.tt.target_active(id)

		if self.tt.active_target:
			all_constraints = self.tt.active_target.get_altitude_constraints_v().keys()
			all_constraints.extend(self.tt.active_target.get_time_constraints_v(self.tt.rect).keys())
			self.ct.set_constraints(all_constraints)
			self.tt.set_visible_constraint(self.ct)

		self.tt.tg.queue_draw()

	def constraint_changed(self,o):
		self.tt.set_visible_constraint(o)
	
class SelectDialog(jsontable.JsonSelectDialog):
	def __init__(self, buttons=None, flags=0, selmode=gtk.SELECTION_SINGLE, extended=True, withpm=False):
		self.ll = login.getProxy().loadJson('/api/labellist')['d']

		jsontable.JsonSelectDialog.__init__(self, '/api/tbyname', {'n':'%', 'e':int(extended), 'ch':1, 'propm':int(withpm)}, buttons=buttons, selmode=selmode, search_column=1,flags=flags)

		self.cb = gtk.combo_box_new_text()
		self.cb.append_text(_('*** ALL ***'))
		self.cb.set_tooltip_markup('Click on the list to filter targets with their label.')

		for l in self.ll:
			self.cb.append_text(l[2])
		self.tids = None
		self.tnames = None

		self.cb.connect('changed',self.filter_t)
		cbh = gtk.Table(2,3,False)

		l = gtk.Label(_('Group:'))
		l.set_alignment(0,0.5)

		cbh.attach(l,0,1,0,1)
		cbh.attach(self.cb,1,2,0,1,gtk.EXPAND|gtk.FILL|gtk.SHRINK)

		self.tn = gtk.Entry()
		self.tn.connect('changed',self.filter_n)

		l = gtk.Label(_('Target name:'))
		l.set_alignment(0,0.5)

		cbh.attach(l,0,1,1,2)
		cbh.attach(self.tn,1,2,1,2,gtk.EXPAND|gtk.FILL|gtk.SHRINK)

		l = gtk.Label(_('Minimal altitude'))
		l.set_alignment(0,0.5)
	
		self.maa = gtk.SpinButton(gtk.Adjustment(-90,-90,90,1,10),digits=0)
		self.maa.connect('changed',lambda x:self.filter.refilter())

		cbh.attach(l,0,1,2,3)
		cbh.attach(self.maa,1,2,2,3,gtk.EXPAND|gtk.FILL|gtk.SHRINK)

		self.vbox.pack_start(cbh,False,False)

		def add_filter(self):
			self.filter = self.js.data.filter_new()
			self.js.tv.set_model(gtk.TreeModelSort(self.filter))

			self.filter.set_visible_func(self.filter_f)

			self.cb.set_active(0)

			self.show_all()

		gobject.idle_add(add_filter,self)

	def filter_t(self,b):
		"""Filter by target type / label."""
		if b.get_active() > 0:
			self.tids = map(lambda x:x[0],login.getProxy().loadJson('/api/tbylabel',{'l':self.ll[b.get_active()-1][0]})['d'])
		else:
			self.tids = None
		self.filter.refilter()
	
	def filter_n(self,e):
		if e.get_text():
			self.tnames = re.compile(e.get_text(), re.I)
		else:
			self.tnames = None
		self.filter.refilter()

	def filter_f(self,model,iter):
		if self.tids:
			v = model.get_value(iter,0)
			if not(v in self.tids):
				return False
		if self.tnames:
			if not(self.tnames.search(model.get_value(iter,1))):
				return False

		if self.maa.get_value_as_int() > -90:
			if model.get_value(iter,4) < self.maa.get_value_as_int():
				return False
		return True

gobject.signal_new('constraint-changed',ConstraintsDisplay,gobject.SIGNAL_RUN_FIRST,gobject.TYPE_NONE,[])
gobject.signal_new('target-changed', TargetColors, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT])
gobject.signal_new('target-active', TargetColors, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, [gobject.TYPE_INT])

if __name__ == '__main__':
  	l = login.Login()
	l.signon()

	t = SelectDialog(extended=True,withpm=True)
	t.connect('destroy',gtk.main_quit)
	t.run()
