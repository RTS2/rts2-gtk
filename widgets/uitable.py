# Class to draw lines connecting elements in display

import gtk
import gettext
import uiwindow
import gobject
import target
import timeplot
import time
import rts2.target

import radec

TOP = 0
RIGHT = 1
BOTTOM = 2
LEFT = 3

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

# value holding possible timeplot display
_timep = None

class LineCell(gtk.DrawingArea):
	"""Creates line for single table element."""
	def __init__(self, exits):
		gtk.DrawingArea.__init__(self)
		self.connect('expose-event',self.expose)

		self.exits = [exits]
		self.width = 1

	def set_line_width(self, width):
		if not(self.width == width):
			self.width = width
			self.queue_draw()

	def add_exits(self, exits):
		self.exits.append(exits)
	
	def expose(self,widget,event):
		context = widget.window.cairo_create()
		context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
		context.clip()

		rect = self.get_allocation()

		context.set_source_rgba(0, 0, 0, 1)
		context.set_line_width(self.width)

		multis = [[0, -1], [1, 0], [0, 1], [-1, 0]]

		w_2 = rect.width / 2 + 1
		h_2 = rect.height / 2 + 1

		# two connecting points - stroke circle
		for e in self.exits:
			def start_point(x, par, par_2):
				if x < 0:
					return 0
				elif x == 0:
					return par_2
				else:
					return x * par
			# draw curve
			context.move_to(start_point(multis[e[0]][0], rect.width, w_2), start_point(multis[e[0]][1], rect.height, h_2))
			context.curve_to(w_2, h_2, w_2, h_2, start_point(multis[e[1]][0], rect.width, w_2), start_point(multis[e[1]][1], rect.height, h_2))
		context.stroke()

class LinePath:
	"""Path formed from lines in table"""
	def __init__(self):
		self.lines = []

	def set_line_width(self, width):
		map(lambda l:l.set_line_width(width), self.lines)

	def set_active(self, active):
		self.set_line_width(10 if active else 1)	

class OnOff(uiwindow.ToggleButton):
	"""Represents anything that can have on-off (true/false) states. Highlights appoproate paths
	based on value of the expression."""
	def __init__(self, master, device, varname, path_true, path_false, tooltip=None):
		uiwindow.ToggleButton.__init__(self, master, device, varname, tooltip)
		self.path_true = path_true
		self.path_false = path_false
	
	def set_rts2(self, varname, value):
		uiwindow.ToggleButton.set_rts2(self, varname, value)
		if value[1]:
			if self.path_true:
				self.path_true.set_active(True)
			if self.path_false:
				self.path_false.set_active(False)
		else:
			if self.path_true:
				self.path_true.set_active(False)
			if self.path_false:
				self.path_false.set_active(True)

class MasterState(gtk.ToggleButton, uiwindow.Value):
	"""Master state - ON"""
	def __init__(self, master, path_off, path_standby, path_on):
		gtk.ToggleButton.__init__(self)
		uiwindow.Value.__init__(self, master)

		self.connid = None

		self.path_on = path_on
		self.path_standby = path_standby
		self.path_off = path_off

		self.set_tooltip_markup('Press to change between <b>on</b> or <b>standby</b> and <b>off</b> state.')
		self.last_state = 0

		self.master.addValue('centrald', '__S__', self)

	def set_rts2(self, varname, value):
		state = value['s']
		self.last_state = state
		state &= 0xff
		if self.connid:
			self.disconnect(self.connid)
		if (state & 0x20) == 0x20 or (state & 0x30) == 0x30:
			self.set_label('Off')
			self.path_on.set_active(False)
			self.path_standby.set_active(False)
			self.path_off.set_active(True)
			self.set_active(False)
		else:
			self.path_off.set_active(False)
			self.set_active(True)
			if state & 0x10:
				self.set_label('Standby')
				self.path_standby.set_active(True)
				self.path_on.set_active(False)
			else:
				self.set_label('On')
				self.path_standby.set_active(False)
				self.path_on.set_active(True)

		self.connid = self.connect('toggled', self.toggled)

	def toggled(self, b):
		if self.get_active():
			if self.last_state & 0x80000000:
				msgb = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_('Confirm switch to ON. When the weather switches to good, the dome will open during the night!'))
			else:
				msgb = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_('Confirm switch to ON. During the night, the dome will open!'))
			ret = msgb.run()
			msgb.destroy()
			if ret == gtk.RESPONSE_YES:
				self.master.jsonProxy.executeCommand('centrald','on')
		else:
			msgb = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_('Confirm switch to OFF. That will interrupt and prevent observations!'))
			ret = msgb.run()
			msgb.destroy()
			if ret == gtk.RESPONSE_YES:
				self.master.jsonProxy.executeCommand('centrald','off')

class MasterState3(gtk.HButtonBox, uiwindow.Value):
	"""Shows OFF, STANDBY and ON buttons in a row, and connect them to centrald state."""
	def __init__(self, master):
		gtk.HButtonBox.__init__(self)
		uiwindow.Value.__init__(self, master)

		self.off = gtk.Button(_('Off'))
		self.standby = gtk.Button(_('Standby'))
		self.on = gtk.Button(_('On'))

		self.add(self.off)
		self.add(self.standby)
		self.add(self.on)

		self.off.connect('clicked', self.clicked)
		self.standby.connect('clicked', self.clicked)
		self.on.connect('clicked', self.clicked)

		self.master.addValue('centrald', '__S__', self)

	def set_offstandbyon(self, off, standby, on):
		self.off.set_sensitive(off)
		self.standby.set_sensitive(standby)
		self.on.set_sensitive(on)

	def set_rts2(self, varname, value):
		state = value['s']
		state &= 0xf0
		if (state & 0x20) == 0x20 or (state & 0x30) == 0x30:
			self.set_offstandbyon(False, True, True)
		elif (state & 0x10) == 0x10:
			self.set_offstandbyon(True, False, True)
		else:
			self.set_offstandbyon(True, True, False)

	def clicked(self, b):
		if b == self.off:
			self.master.jsonProxy.executeCommand('centrald', 'off')
		elif b == self.standby:
			self.master.jsonProxy.executeCommand('centrald', 'standby')
		elif b == self.on:
			self.master.jsonProxy.executeCommand('centrald', 'on')

class MasterNight(gtk.Frame, uiwindow.Value):
	def __init__(self, master, path_night, path_day):
		gtk.Frame.__init__(self)
		uiwindow.Value.__init__(self, master)

		self.nightl = gtk.Label()
		self.nightev = gtk.EventBox()
		self.nightev.add(self.nightl)
		self.add(self.nightev)

		self.path_night = path_night
		self.path_day = path_day

		self.master.addValue('centrald', '__S__', self)

		self.set_tooltip_markup('Shows system state')
	
	def set_rts2(self, varname, value):
		state = value['s']
		states = ['Day', 'Evening', 'Dusk', 'Night', 'Dawn', 'Morning']
		try:
			self.nightl.set_text(states[state & 0x0f])
		except IndexError,ie:
			self.nightl.set_text('OFF')
		if (state & 0x30) or (state & 0x0f) in [0, 1, 5]:
			self.nightev.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('yellow'))
			self.path_night.set_active(False)
			self.path_day.set_active(True)
		elif (state & 0x0f) in [2, 3, 4]:
			self.nightev.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('green'))
			self.path_night.set_active(True)
			self.path_day.set_active(False)
		else:
			self.nightev.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color('red'))
			self.path_night.set_active(False)
			self.path_day.set_active(False)

class LimitButton(gtk.Button, uiwindow.Value):
	def __init__(self, master, device, varname, path_good=None, path_failed=None):
		gtk.Button.__init__(self)
		uiwindow.Value.__init__(self, master)
		self.device = device
		self.varname = varname
		
		self.path_good = path_good
		self.path_failed = path_failed

		self.master.addValue(device, varname, self)

		self.set_tooltip_markup('Click to change limit')

		self.connect('clicked', self.clicked)

	def set_rts2(self, varname, value):
		if self.master.jsonProxy.getValueError(self.device, self.varname):
			self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color("red"))
		elif self.master.jsonProxy.getValueWarning(self.device, self.varname):
			self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color("yellow"))
		else:
			self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color("green"))
			if self.path_good:
				self.path_good.set_active(True)
			if self.path_failed:
			  	self.path_failed.set_active(False)
			return

		if self.path_good:
			self.path_good.set_active(False)
		if self.path_failed:
		  	self.path_failed.set_active(True)

	def clicked(self, b):
		pass

class RaDecLabel(gtk.Label, uiwindow.Value):
	def __init__(self, master, device, varname):
		gtk.Label.__init__(self)
		uiwindow.Value.__init__(self, master)
		self.master.addValue(device, varname, self)

	def set_rts2(self, varname, value):
		(signra,rah,ram,ras) = radec.to_hms(value[1]['ra'] / 15.0)
		(signdec,dech,decm,decs) = radec.to_hms(value[1]['dec'])

		self.set_label("RA {0:02}:{1:02}:{2:06.3f} DEC {3}{4:02}:{5:02}:{6:05.2f}".format(rah, ram, ras, signdec, dech, decm, decs))

class LimitLabel(LimitButton):
	def __init__(self, master, device, varname, limitvar, text, limithelp, path_good=None, path_failed=None):
		LimitButton.__init__(self, master, device, varname, path_good=path_good, path_failed=path_failed)
		self.set_label(text)

		self.limitvar = limitvar
		self.text = text
		self.limithelp = limithelp

		self.connect('button-press-event', self.pressed)

		self.master.addValue(device, limitvar, self)

	def set_rts2(self, varname, value):
		s = '<'
		v = self.master.jsonProxy.getSingleValue(self.device, self.varname)
		l = self.master.jsonProxy.getValue(self.device, self.limitvar)
		if v > l:
			s = '>'
		self.set_label(self.text.format(v=v, l=l, s=s))
		LimitButton.set_rts2(self, varname, value)
	
	def clicked(self, b):
		d = gtk.Dialog('Set new limit value', self.get_toplevel(), gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

		d.get_content_area().pack_start(gtk.Label(self.limithelp))
		e = gtk.Entry()
		e.set_text(str(self.master.jsonProxy.getValue(self.device, self.limitvar)))
		d.get_content_area().pack_end(e)
		d.show_all()

		if d.run() == gtk.RESPONSE_ACCEPT:
			self.master.jsonProxy.setValue(self.device, self.limitvar, e.get_text())
		d.hide()
	
	def pressed(self, b, e):
		if e.button == 3:
			_timep = LimitPlot(self.device, self.varname)
			w = gtk.Window()
			w.add(_timep)
			w.show_all()

class LimitTimeout(LimitButton):
	def __init__(self, master, device, varname, text='{0}', path_good=None, path_failed=None):
		LimitButton.__init__(self, master, device, varname, path_good=path_good, path_failed=path_failed)
		self.text = text
		self.to_time = None

		self.set_tooltip_markup('Click to reset timer to 0')

	def set_rts2(self, varname, value):
		if value[1] > time.time():
		  	if self.to_time is None:
				self.to_time = value[1]
				gobject.timeout_add(50, self.update_time)
			else:
				self.to_time = value[1]
		else:
			self.set_label(self.text.format('None'))
			self.to_time = None
		LimitButton.set_rts2(self, varname, value)

	def clicked(self, b):
		msgb = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=_('Are you sure to reset timeout?'))
		ret = msgb.run()
		msgb.destroy()
		if ret == gtk.RESPONSE_YES:
			self.master.jsonProxy.executeCommand(self.device, 'reset_next', True)
	
	def update_time(self):
		if self.to_time is None or self.to_time < time.time():
		  	self.set_label(self.text.format('None'))
			self.to_time = None
			return False
		self.set_label(self.text.format("{0:.1f} s".format(self.to_time - time.time())))
		return True

class LimitPlot(timeplot.TimePlot, uiwindow.Value):
	def __init__(self, master, device, varname):
		timeplot.TimePlot.__init__(self, time.time(), 60)
		uiwindow.Value.__init__(self, master)

		self.master.addValue(device, varname, self)

	def set_rts2(self, varname, value):
		n = time.time()
		self.points = self.points[-10:]
		self.points.append([n, value[1]])
		self.x_ruler.lower = self.points[0][0]
		self.y_ruler.upper = n + 1
		self.auto_y_range()
		self.queue_draw()

class TargetButton(gtk.Button, uiwindow.Value):
	def __init__(self, master, device, varname, frmt=None):
		gtk.Button.__init__(self)
		uiwindow.Value.__init__(self, master)
		self.device = device
		self.varname = varname
		self.frmt = frmt

		self.master.addValue(device, varname, self)

		self.connect('clicked', self.clicked)
		self.last_target = None
	
	def set_rts2(self, varname, value):
		if self.last_target is None or self.last_target.id != value[1]:
			self.last_target = rts2.target.Target(value[1])
			self.last_target.reload()
		if self.frmt:
			self.set_label(self.frmt.format(self.last_target))
		else:
			self.set_label('{0.name} (#{1.id})'.format(self.last_target))
		self.set_sensitive(value[1] > 0)
	
	def clicked(self, b):
		td = target.TargetDialog(self.master.jsonProxy.getValue(self.device, self.varname))
		td.show()

class ParkButton(gtk.Button, uiwindow.Value):
	"""Button to execute telescope parking."""
	def __init__(self, master, telescope):
		gtk.Button.__init__(self, "Park")
		uiwindow.Value.__init__(self, master)

		self.telescope = telescope

		self.is_standby = False
		self.is_parked = False

		self.connect('clicked', self.clicked)

		self.master.addValue('centrald', '__S__', self)
		self.master.addValue(self.telescope, '__S__', self)

	def set_rts2(self, varname, value):
		if varname == 'centrald.__S__':
			self.is_standby = value['s'] & 0x30
		if varname == self.telescope + '.__S__':
                        self.is_parked = not(value['s'] & 0x06)
			if value['s'] & 0x04:
				self.set_label(_('Parking'))
			elif value['s'] & 0x02:
                                self.set_label(_('Parked'))
			else:
				self.set_label(_('Park'))

		self.set_sensitive(self.is_standby and self.is_parked)
			
	def clicked(self, b):
		self.master.jsonProxy.executeCommand(self.telescope, "park")


class UITable(gtk.Table):
	paths = []
	def __init__(self, rows=1, columns=1, homogeneous=False):
		gtk.Table.__init__(self, rows, columns, homogeneous)

		self.line_cells = {}

	def create_path(self, from_c, to_c, from_r, to_r):
		"""Create path in table."""
	
		p = LinePath()

		def create_or_modify(col, row, exits):
			try:
				l = self.line_cells[row][col]
				l.add_exits(exits)
				return l
			except KeyError,ke:
				l = LineCell(exits)
				self.attach(l, col, col + 1, row, row + 1, gtk.EXPAND | gtk.SHRINK | gtk.FILL, gtk.EXPAND | gtk.SHRINK | gtk.FILL)
				try:
					self.line_cells[row][col] = l
				except KeyError,ke:
					self.line_cells[row] = {}
					self.line_cells[row][col] = l
				return l

		if from_r < to_r:		
			if from_c < to_c:
				for c in range(from_c, to_c):
					p.lines.append(create_or_modify(c, from_r, [LEFT, RIGHT]))
				p.lines.append(create_or_modify(to_c, from_r, [LEFT, BOTTOM]))
				for r in range(from_r + 1, to_r):
					p.lines.append(create_or_modify(to_c, r, [TOP, BOTTOM]))
			elif from_c == to_c:
				for r in range(from_r, to_r):
					p.lines.append(create_or_modify(from_c, r, [TOP, BOTTOM]))
			else:
				for c in range(to_c + 1, from_c):
					p.lines.append(create_or_modify(c, from_r, [RIGHT, LEFT]))
				p.lines.append(create_or_modify(to_c, from_r, [RIGHT, BOTTOM]))
				for r in range(from_r + 1, to_r):
					p.lines.append(create_or_modify(to_c, r, [TOP, BOTTOM]))
		else:
			if from_c < to_c:
				for c in range(from_c, to_c):
					p.lines.append(create_or_modify(c, from_r, [LEFT, RIGHT]))
				p.lines.append(create_or_modify(to_c, from_r, [LEFT, TOP]))
				for r in range(to_r + 1, from_r):
					p.lines.append(create_or_modify(to_c, r, [BOTTOM, TOP]))
			elif from_c == to_c:
				for r in range(to_r, from_r):
					p.lines.append(create_or_modify(from_c, r, [BOTTOM, TOP]))
			else:
				for c in range(to_c + 1, from_c):
					p.lines.append(create_or_modify(c, from_r, [RIGHT, LEFT]))
				p.lines.append(create_or_modify(to_c, from_r, [RIGHT, TOP]))
				for r in range(to_r + 1, from_r):
					p.lines.append(create_or_modify(to_c, r, [BOTTOM, TOP]))

		self.paths.append(p)
		return p
