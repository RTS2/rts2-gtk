# Draw windows from JSON form.
# Copyright (C) 2011-2016 Petr Kubanek, Institute of Physics <kubanek@fzu.cz>
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
import pango
import gobject
import jsontable
import math
import sys
import time
import gettext
import radec
import threading
import traceback
import Queue
import rts2.json
import urllib

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class Value:
	def __init__(self, master):
		"""Construct RTS2 bind value.
		@param master Master RTS2 connection (UIFrame at the moment)"""
		self.master = master
	
	def set_rts2(self, varname, value):
		print value

class Entry(gtk.Entry, Value):
	def __init__(self,master,device,varname):
		gtk.Entry.__init__(self)
		Value.__init__(self, master)
		self.connect('key-press-event', self.key_press)

		self.master.addValue(device, varname, self)
		self.device = device
		self.varname = varname

	def set_rts2(self, varname, value):
		if not(self.flags() & gtk.HAS_FOCUS):
			self.set_text(str(value[1]))
	
	def key_press(self, widget, event):
		if event.keyval == gtk.keysyms.Return:
			self.master.jsonProxy.setValue(self.device, self.varname, self.get_text())

class SelectionComboEntry(gtk.ComboBoxEntry,Value):
	def __init__(self, master, device, varname):
		liststore = gtk.ListStore(gobject.TYPE_STRING)
		gtk.ComboBoxEntry.__init__(self, gtk.ListStore(gobject.TYPE_STRING), 0)
		Value.__init__(self, master)

		for x in login.getProxy().getSelection(device, varname):
			self.append_text(x)

		self.master.addValue(device, varname, self)
		self.device = device
		self.varname = varname

		self.connect('changed', self.changed)
	
	def set_rts2(self, varname, value):
		self.set_active(int(value[1]))
	
	def changed(self, b):
		self.master.jsonProxy.setValue(self.device, self.varname, b.get_active())

class Label(gtk.EventBox, Value):
	def __init__(self, master, device, varname, frmt=None):
		gtk.EventBox.__init__(self)
		self.label = gtk.Label()
		self.label.set_alignment(1, 0.5)
		Value.__init__(self, master)
		self.device = device
		self.varname = varname
		self.frmt = frmt
		self.add(self.label)

		self.master.addValue(device, varname, self)
	
	def set_rts2(self, varname, value):
		if self.frmt:
			self.label.set_text(self.frmt.format(value[1]))
		else:
			self.label.set_text(str(value[1]))

class StateProgress(gtk.ProgressBar, Value):
	def __init__(self, master, device):
		gtk.ProgressBar.__init__(self)
		Value.__init__(self,master)
				
		self.master.addValue(device, '__S__',self)
	
	def set_rts2(self, varname, value):
		print 'state', varname, value

class StateProgressCam(gtk.ProgressBar, Value):
        def __init__(self, master, device):
                gtk.ProgressBar.__init__(self)
                Value.__init__(self,master)
                #self.set_text('Camera Exposure')
                self.master.addValue(device, '__S__', self)

        def set_rts2(self, varname, value):
		if value['s'] & 0x002:
			self.set_text('Camera Reading')
			gtk.timeout_add(200, self.timer, value)
		elif value['s'] & 0x001:
			self.set_text('Camera Exposing')
			gtk.timeout_add(200, self.timer, value)
		else:	
			self.set_text('Camera IDLE')
			self.set_fraction(0)
		
		#gtk.timeout_add(200, self.timer, value)

	def timer(self,value):
		if value['st'] < time.time():
			return False
		fraction = (time.time()-value['sf'])/(value['st']-value['sf'])
		self.set_fraction(max(0, min(1, fraction)))
		return True	
	
class ToggleButton(gtk.ToggleButton, Value):
	def __init__(self, master, device, varname, tooltip=None):
		gtk.ToggleButton.__init__(self)
		Value.__init__(self, master)
		self.device = device
		self.varname = varname

		if tooltip is not None:
			self.set_tooltip_markup(tooltip)
		self.connect('toggled', self.toggled)

		self.master.addValue(device, varname, self)

	def set_rts2(self, varname, value):
		if value[1]:
			self.set_active(True)
			self.set_label(_('On'))
		else:
			self.set_active(False)
			self.set_label(_('Off'))

	def toggled(self, b):
		self.master.jsonProxy.setValue(self.device, self.varname, self.get_active())
		if self.get_active():
			self.set_label(_('Off'))
		else:
			self.set_label(_('On'))

class WWWImage(gtk.Image):
	def __init__(self, url=None, reload_interval=None, scale=None):
		gtk.Image.__init__(self)
		self.scale = scale
		self.pb = None
		self.image_error = None

		# draw cross on this position
		self.alt = None
		self.az = None

		if url and reload_interval:
			self.reload_url(url, reload_interval)
			return
		if url:
			self.loadURL(url)

	def set_alt_az(self, alt, az):
		self.alt = alt
		self.az = az
		if self.pb:
			self.redraw()

	def redraw(self):
		if self.pb is None:
			self.pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, 300, 300)
			self.pb.fill(int(str(self.get_style().bg[gtk.STATE_NORMAL])[1:] + '00', 16))
		
		pixmap, mask = self.pb.render_pixmap_and_mask()
		if self.alt is not None and self.az is not None:
			# draw on top rectangle
			cm = pixmap.get_colormap()
			gc = pixmap.new_gc(foreground=cm.alloc_color('red'))

			r = (90 - self.alt) / 90.0

			w = self.pb.get_width()
			h = self.pb.get_height()

			c_x = w * 299 / 640.0
			c_y = h * 230 / 480.0

			r_x = r * (w * 200 / 480.0)
			r_y = r * (h * 200 / 480.0)

			an = math.radians(self.az)

			x = int(c_x + r_x * math.sin(an))
			y = int(c_y + r_y * math.cos(an))

			if w > x + 10 and h > y + 10:
				pixmap.draw_rectangle(gc, False, x - 10, y - 10, 20, 20)

		if self.image_error:
			# print image error on top of the image..
			pc = self.get_pango_context()
			layout = pango.Layout(pc)
			layout.set_width(self.pb.get_width())
			layout.set_text(self.image_error)

			cm = pixmap.get_colormap()
			gc = pixmap.new_gc(foreground=cm.alloc_color('red'))

			pixmap.draw_layout(gc, self.pb.get_width() / 2 - layout.get_pixel_size()[0] / 2, self.pb.get_height() / 2, layout)

		self.set_from_pixmap(pixmap, mask)
		self.queue_draw()
		
	def loadURL(self, url, reload_interval=None):
		try:
			f = urllib.urlopen(url)
			pixbufloader = gtk.gdk.PixbufLoader()
			pixbufloader.write(f.read())
			pixbufloader.close()
			if pixbufloader.get_pixbuf() is None:
				raise Exception('Cannot load image {0}'.format(url))
			self.pb = pixbufloader.get_pixbuf()
			if self.scale:
				self.pb = self.pb.scale_simple(self.scale[0], self.scale[1], gtk.gdk.INTERP_BILINEAR)

			self.image_error = None

		except Exception,ex:
			traceback.print_exc()
			self.image_error = 'Cannot load image at URL: {0}'.format(url)

		finally:		
			gobject.idle_add(self.redraw)

			if reload_interval:
				gobject.timeout_add(reload_interval, self.reload_url, url, reload_interval)

	def reload_url(self, url, reload_interval):
		threading.Thread(target=self.loadURL, args=(url,reload_interval,)).start()
		return False
	
	def clicked(self, w, e):
		print e	
			
class FileSelection(gtk.HBox, Value):
	def __init__(self, master, device, varname):
		gtk.HBox.__init__(self)
		Value.__init__(master)
		
		self.entry = Entry(master, device, varname)
		self.pack_start(self.entry, True, True)
		b = gtk.Button(label='...')
		b.connect('clicked', self.selectfile)
		self.pack_end(b, False)

	def selectfile(self,b):
		d = gtk.FileChooserDialog(title='Select {0}'.format(self.entry.varname),buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		d.set_default_response(gtk.RESPONSE_OK)

		if self.filter is not None:
			fil = gtk.FileFilter()
			fil.set_name(self.filter)
			fil.add_pattern(self.filter)
			d.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		d.add_filter(fil)

		d.set_filter(d.list_filters()[0])

		d.set_filename(self.master.jsonProxy.getValue(self.entry.device,self.entry.varname))

		res = d.run()
		if res == gtk.RESPONSE_OK:
			self.entry.set_text(d.get_filename())
			self.entry.changed(None)
		d.destroy()

class Command(gtk.Button):
	"""Command button - if clicked, send command."""
	def __init__(self,jsonProxy,device,command,**kvargs):
		gtk.Button.__init__(self,**kvargs)
		self.jsonProxy = jsonProxy
		self.device = device
		self.command = command

		self.connect('clicked',self.clicked)

	def clicked(self,b):
		self.jsonProxy.executeCommand(self.device,self.command)

def _getValueBox(master,t,je):
	"""Return value box for given value type."""
	f = None

	if t == 'text':
		f = gtk.Label(_(je['text']))
		f.set_use_markup(True)
		f.set_alignment(0, 0.5)
		return f

	i = je['value'].find('.')
	device = je['value'][:i]
	value = je['value'][i+1:]
	frmt = je['format'] if je.has_key('format') else None

	if t == 'eval':
		f = Entry(master,device, value)
	elif t == 'bool':
		f = ToggleButton(master,device, value)
	elif t == 'vlab':
		f = Label(master,device, value, frmt=frmt)
	elif t == 'filesel':
		f = FileSelection(master,device, value)
	try:
		f.set_tooltip_markup('<b>{0}.{1}</b>:{2}'.format(device, value, json.JSONProxy().getVariable(device, value)[4]))
	except Exception,ex:
		f.set_tooltip_markup('<b>missing value</b>: {0}'.format(str(ex)))

	return master.addValue(device, value, f)

def _createForm(parent, master, je):
	"""Create form from json element, add it to parent."""
	for x in je:
		_createElement(parent, master, x)

def _createElement(parent, master, je):
	t = je['t']
	f = None
	if t == 'vbox':
		f = gtk.VBox()
		_createForm(f, master, je['c'])
		parent.add(f)
	elif t == 'hbox':
		f = gtk.HBox()
		_createForm(f, master, je['c'])
		parent.add(f)
	elif t == 'vtable':
		f = Table(master, je['c'])
		parent.add(f)
	elif t == 'notebook':
		f = Notebook(master, je['c'])
		parent.add(f)
	elif t == 'form':
		f = gtk.Button(label=je['name'])
		f.connect('clicked', _createWindow, je)
		parent.add(f)
	elif t == 'target_b':
		f = gtk.Button(label=je['name'])
		idn = login.getProxy().getValue(je['device'],je['value'])
		if idn > 0:
			a = login.getProxy().loadJson('/api/tbyid',{'id':idn})
			f.set_label('{0} ({1})'.format(a['d'][0][1],idn))
		f.connect('clicked',self.selectTarget,je)
		parent.add(f)
	else:
		f = _getValueBox(master,t,je)
		if f is None:
			print >>sys.stderr, 'unknow type {0}'.format(t)
		else:
			parent.pack_start(f,False)
	return f

def _createWindow(b, je):
	"""Create window from the given je element. Parses form from URL, display it."""
	w = UIWindow(je['url'],title=je['name'])
	w.show()

class Table(gtk.Table):
	"""Create table instance."""
	def __init__(self, master, je):
		gtk.Table.__init__(self)
		self.set_row_spacings(3)
		self.set_col_spacings(3)
		last_x = 0
		last_y = 0
		for x in je:
			(last_x, last_y) = x['a'].split(':')
			last_x = int(last_x)
			last_y = int(last_y)
			self.attach(_getValueBox(master, x['t'], x), last_x, last_x+1, last_y, last_y+1, gtk.SHRINK | gtk.FILL, gtk.SHRINK)
	
class Notebook(gtk.Notebook):
	def __init__(self, master, je):
		gtk.Notebook.__init__(self)
		for x in je:
		  	f = gtk.Frame()
			_createElement(f, master, x['c'])
			self.append_page(f, tab_label=gtk.Label(x['label']))

class UIFrame(gtk.Frame):
	def __init__(self,jsonProxy,url=None):
		gtk.Frame.__init__(self)

		self.__values = {}
		self.__new_values = Queue.Queue()

		self.jsonProxy = jsonProxy
		self.url = url
		if self.url is not None:
			self.loadJson(self)
			self.show_all()
			self.start_push()

	def addValue(self, device, value, element):
		"""Add value to values being pushed by RTS2."""
		self.__new_values.put((device, value, element))

		return element

	def start_push(self):
		def __thread(self):
			a = []
			# construct new _values array
			while not self.__new_values.empty():
				qe = self.__new_values.get_nowait()
				try:
					self.__values[qe[0]].append((qe[1], qe[2]))
				except KeyError,ke:
					self.__values[qe[0]] = [(qe[1], qe[2])]
				self.__new_values.task_done()
						
			for x in self.__values.keys():
				for y in self.__values[x]:
					if (x,y[0]) not in a:
						a.append((x,y[0]))

			r = self.jsonProxy.getResponse('/api/push', args=a)
			while self.__new_values.empty():
				res = self.jsonProxy.chunkJson(r)
				d = res['d']
				if res.has_key('v'):
					vals = res['v']
					for v in vals.keys():
						for f in self.__values[d]:
							self.jsonProxy.devices[d][v] = vals[v]
							if f[0] == v:
								gobject.idle_add(f[1].set_rts2, '{0}.{1}'.format(d, v), vals[v])
				if res.has_key('s'):
					for f in self.__values[d]:
						if f[0] == '__S__':
							gobject.idle_add(f[1].set_rts2, '{0}.{1}'.format(d, '__S__'), res)

		def __thread_loop(self):
			while True:
				try:
					__thread(self)
				except Exception,ex:
					traceback.print_exc()
					time.sleep(5)
					try:
						self.jsonProxy.hlib = self.jsonProxy.newConnection()
					except Exception,ex:
						self.jsonProxy.hlib = None

		
		th = threading.Thread(target=__thread_loop,args=(self,))
		th.setDaemon(True)
		th.start()

	def loadJson(self,parent):
		form = self.jsonProxy.loadJson(self.url,{})
		self.min_width=form['mw']
		self.min_height=form['mh']
		self.main = _createElement(parent, self, form)

	def selectTarget(self,b,je):
		"""Enable users to select target."""
		def __select(self):
			d = jsontable.JsonSelectDialog('/api/tbyname',{'n':'%','e':1},buttons=[(_('Set'),1),(_('_Cancel'),2)],selmode=gtk.SELECTION_SINGLE)
			if d.run() == 1:
			  	self.jsonProxy.setValue(je['device'],je['value'],d.getSelected(0)[0])
				b.set_label('{0} ({1})'.format(d.getSelected(1)[0],d.getSelected(0)[0]))
			d.hide()

		threading.Thread(target=__select,args=(self,)).start()
