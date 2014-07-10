#!/usr/bin/env python
"""Load and display table requested from JSON API."""
#
# @author Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import login

import gtk
import gobject
import gettext
import radec
import math
import urllib

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

import login
import radec
import datetime
import threading
import json

gtk.gdk.threads_init()

# sorting function which guarantee order by path number if members are equal
def _sort_func(model,i1,i2,user_data):
	ret = cmp(model[i1][user_data],model[i2][user_data])
	if ret == 0:
		return cmp(model.get_path(i1),model.get_path(i2))
	return ret

# Class representing as ListStore where data can be obtained from table parsed from JSON data.
#
# @author Petr Kubanek, Institute of Physics <kubanek@fzu.cz>
class JsonList(gtk.ListStore):
	def __init__(self, radio_select=None):
		# dummy init, column types will be overwritten
		gtk.ListStore.__init__(self, int)

		self.radio_select = radio_select

		self.names = []
		self.cols = []
		self.types = []
		self.renders = []

	def data_header(self, header):
		self.names = []
		self.cols = []
		self.types = []
		self.renders = []

		for x in header:
			t = x['t']
			self.names.append(x['n'])
			self.cols.append(x['c'])
			if t=='r':
				self.types.append(float)
				self.renders.append(lambda column,cell,model,iter,ud:cell.set_property('text', radec.ra_string(model.get_value(iter,ud))))
			elif t=='d':
				self.types.append(float)
				self.renders.append(lambda column,cell,model,iter,ud:cell.set_property('text', radec.dec_string(model.get_value(iter,ud))))
			elif t=='ip':
				self.types.append(str)
				self.renders.append(None)
			elif t=='n':
				self.types.append(int)
				self.renders.append(None)
			elif t == 't' or t == 'tD' or t == 'tT':
				self.types.append(str)
				self.renders.append(RenderTime(t).render_time)
			elif t == 'b':
				self.types.append(bool)
				self.renders.append(None)
			elif t == 'dur':
				self.types.append(float)
				self.renders.append(None)
			elif t == 'object':
				self.types.append(gobject.TYPE_PYOBJECT)
				self.renders.append(None)
			else:
				self.types.append(str)
				self.renders.append(None)

		if self.radio_select:
			self.types.append(bool)

		self.set_column_types(*self.types)	
	
	def reload(self,d):
		for x in d:
			self.append_row(x)

	def append_row(self, x):
		for el in range(0,len(x)):
			if x[el] is None:
				x[el] = -float('inf')
		if self.radio_select:
		  	x.append(False)
		self.append(x)

class RenderTime:
	def __init__(self,t):
		self.t = t
	
 	def render_time(self,column,cell,model,iter,ud):
		try:
			m = model.get_value(iter,ud)
			if m is None or math.isinf(float(m)):
				cell.set_property('text','---')
			elif self.t == 't':
				cell.set_property('text', datetime.datetime.fromtimestamp(int(round(float(m)))))
			elif self.t == 'tD':
				cell.set_property('text', datetime.date.fromtimestamp(int(round(float(m)))))
			elif self.t == 'tT':
				cell.set_property('text', datetime.datetime.fromtimestamp(int(round(float(m)))).time())
			else:
				cell.set_property('text','unknow {0}'.format(self.t))
		except ValueError,v:
			cell.set_property('text','---')


class JsonTable(gtk.ScrolledWindow):
	# Constructor for list based on JSON table data.
	#
	# @param filter_func  if not none, used as filtering function

	def __init__(self,path,args={},selmode=gtk.SELECTION_SINGLE,search_column=-1,filter_func=None,data=None,radio_select=None,radio_select_func=None, progressbar=None):
		gtk.ScrolledWindow.__init__(self)
		self.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

		self.data = JsonList(radio_select)
		if data is None:
			r = login.getProxy().getResponse(path, args=args, hlib=login.getProxy().newConnection())
			if r.getheader('transfer-encoding') == 'chunked':
				# read first chunk, then read data in thread
				res = login.getProxy().chunkJson(r)
				self.data.data_header(res['h'])
				def __load_thread(self, rows, r, progressbar):
					for i in range(1, rows + 1):
						res = login.getProxy().chunkJson(r)
						def _add_row(data, res, progressbar, rows, i):
							data.append_row(res)
							if progressbar:
								progressbar.set_fraction(i / float(rows))
								progressbar.set_text('{0} of {1}'.format(i, rows))

						gobject.idle_add(_add_row, self.data, res, progressbar, rows, i)
				threading.Thread(target=__load_thread, args=(self, res['rows'], r, progressbar, )).start()
			else:
				data = json.loads(r.read())
				self.data.data_header(data['h'])
				self.data.reload(data['d'])
		else:
			self.data.data_header(data['h'])
			self.data.reload(data['d'])

		if filter_func:
			self.data = self.data.filter_new()
			self.data.set_filter_func(filter_func)

		self.sm = gtk.TreeModelSort(self.data)
		self.tv = gtk.TreeView(self.sm)
		self.tv.set_rules_hint(True)
		self.tv.get_selection().set_mode(selmode)

		# set sortable functions for 
		for i in range(0,self.sm.get_n_columns()):
			self.sm.set_sort_func(i,_sort_func,i)

		if radio_select is not None:
			col = gtk.TreeViewColumn(radio_select)
			col.set_expand(False)
			cel = gtk.CellRendererToggle()
			cel.set_property('radio',True)
			if radio_select_func is not None:
				cel.connect('toggled',radio_select_func)
			col.pack_start(cel)
			self.tv.append_column(col)
			col.add_attribute(cel,'active',len(self.data.names))

		for i in range(0,len(self.data.names)):
			col = gtk.TreeViewColumn(self.data.names[i])
			col.set_sort_column_id(i)
			if self.data.types[i] == str:
				col.set_expand(True)
			else:
				col.set_expand(False)
			if self.data.types[i] == bool:
				cel = gtk.CellRendererToggle()
				col.pack_start(cel)
				col.add_attribute(cel,'active',i)
			elif self.data.types[i] == gobject.TYPE_PYOBJECT:
				continue
			else:
				cel = gtk.CellRendererText()
				col.pack_start(cel)
				if self.data.renders[i] is not None:
					col.set_cell_data_func(cel,self.data.renders[i],self.data.cols[i])  
				else:	
					col.set_attributes(cel,text=self.data.cols[i])

			self.tv.append_column(col)

		self.tv.set_reorderable(True)
		self.tv.set_search_column(search_column)

		self.add(self.tv)

	def reload(self,path,args={},data=None):
		self.tv.set_model(None)
		self.data.clear()
		if data is None:
			self.data.reload(login.getProxy().loadJson(path,args)['d'])
		else:
			self.data.reload(data)
		self.tv.set_model(self.sm)

	def append(self,path,args={},data=None):
		self.tv.set_model(None)
		if data is None:
			self.data.reload(login.getProxy().loadJson(path,args)['d'])
		else:
			self.data.reload(data)
		self.tv.set_model(self.sm)

class JsonSelectDialog(gtk.Dialog):
	def __init__(self, path, args, buttons=[(_('Add'),1),(_('Cancel'),2)], selmode=gtk.SELECTION_SINGLE, search_column=-1, flags=0):
		gtk.Dialog.__init__(self, flags=flags)
		self.set_geometry_hints(min_width=500, min_height=400)

		self.progressbar = gtk.ProgressBar()
		self.action_area.pack_start(self.progressbar, True, True)
		self.js = JsonTable(path, args, selmode, search_column, progressbar=self.progressbar)
		
		self.vbox.pack_end(self.js,True)
		if buttons is not None:
			for x in buttons:
				self.add_button(*x)
		# pack statusbar
		self.set_focus(self.js.tv)

		gobject.idle_add(self.show_all)
	
	def getSelected(self,i):
		(model,sel) = self.js.tv.get_selection().get_selected_rows()
		ret=[]
		for s in sel:
			ret.append(model.get_value(model.get_iter(s),i))
		return ret

if __name__ == '__main__':
	l = login.Login()
	l.signon()

	d = JsonSelectDialog('/api/tbyname',{'n':'%','ch':1,'e':1})
	hb = gtk.HBox(spacing=5)
	hb.pack_start(gtk.Label(_('Part')),False,False)
	url = gtk.Entry()
	url.set_text('/api/tbyname?n=%&ch=1&e=1')
	hb.pack_start(url)

	def reload_table(b):
		text = url.get_text()
		params = {}
		i = text.find('?')
		if i > 0:
			p = text[i+1:]
			for e in p.split('&'):
				pn,pv = e.split('=')
				params[pn] = pv
			text = text[:i]
		text = urllib.quote(text)
		d.vbox.remove(d.js)
		d.js = JsonTable(text, params, progressbar=d.progressbar)
		d.vbox.pack_end(d.js,True)
		gobject.idle_add(d.show_all)

	b = gtk.Button(_('Load'))
	b.connect('clicked',reload_table)
	hb.pack_end(b,False,False)
	d.vbox.pack_start(hb,False,False)
	gobject.idle_add(d.show_all)
	d.run()
	print d.getSelected(0)
