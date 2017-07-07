#!/usr/bin/env python
#
# Queues frame - to select queues
#
# Petr Kubanek <petr@kubanek.net>

import gtk
import gettext
import gobject
import login
import queue
import targets
import time
import nights
import rts2
import rts2.rtsapi
import uiwindow
import xml.dom.minidom

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class Queue(uiwindow.Value):
	"""Construct queue block. All elements attach to table on given row."""
	def __init__(self, master, qname, table, row, index=None, label=None, dont_disable=False):
		uiwindow.Value.__init__(self, master)
		master.addValue('SEL', qname + '_ids', self)
		master.addValue('SEL', qname + '_enabled', self)
		master.addValue('SEL', qname + '_start', self)
		master.addValue('SEL', qname + '_end', self)
		master.addValue('SEL', qname + '_qid', self)
		master.addValue('SEL', 'last_queue', self)

		self.index = index

		self.qname = qname
		self.table = table
		self.q = None

		if not(label):
			label = qname

		self.l = gtk.Label('<span size="x-large">{0}</span>'.format(label))
		self.l.set_use_markup(True)
		self.l.set_alignment(0, 0.5)

		self.le = gtk.EventBox()
		self.le.basecolor = self.le.style.bg[gtk.STATE_NORMAL]
		self.le.add(self.l)

		self.table.attach(self.le, 0, 1, row, row+1, yoptions=gtk.FILL, xpadding=5)

		self.cl = gtk.Label()
		self.table.attach(self.cl, 1, 2, row, row+1, gtk.FILL, gtk.FILL, xpadding=10)

		readonly = not(self.master.jsonProxy.getVariable('SEL',self.qname + '_queing')[0] & rts2.rtsapi.RTS2_VALUE_WRITABLE)

		qe = None
		if readonly:
			qe = gtk.Button(label=_('View'))
			qe.connect('clicked',self.view)
			self.selbox = None
		else:
			if dont_disable:
				self.master.jsonProxy.setValue('SEL',self.qname + '_enabled', True)
				self.selbox=None
			else:
				self.selbox = gtk.CheckButton(label=_('enabled'))
				self.selbox.connect('clicked',self.select_queue)
				self.table.attach(self.selbox, 2, 3, row, row+1, gtk.FILL, gtk.FILL, xpadding=15)

			qe = gtk.Button(label=_('Edit'))
			qe.connect('clicked',self.edit)
		self.table.attach(qe, 3, 4, row, row+1, gtk.FILL, gtk.FILL, xpadding=5)

		self.tl = targets.TargetLabel(None, colorBellow=True, invalidText=' ', withStartTime=True)
		self.table.attach(self.tl, 0, 4, row+1, row+2, yoptions=gtk.FILL, xpadding=5)

	def set_rts2(self, varname, value):
		if varname == 'SEL.' + self.qname + '_enabled':
			if self.selbox:
				self.selbox.set_active(value[1])
		elif varname == 'SEL.' + self.qname + '_ids':
			self.cl.set_text(str(len(value[1])))
			self.tl.set_id(len(value[1]) > 0 and value[1][0] or None)
		elif varname == 'SEL.' + self.qname + '_start':
			if len(value[1]) and value[1][0] is not None:
				self.tl.set_start(value[1][0])
			else:
				self.tl.set_start(None)
			self.tl.reload()
		elif varname == 'SEL.last_queue':
			self.le.modify_bg(gtk.STATE_NORMAL,(value[1] == self.index and gtk.gdk.Color('green') or self.le.basecolor))

	def window_create(self):
		if self.q is None:
			self.q = queue.QueueFrame(self.master, self.qname)
			self.w = gtk.Window()
			self.w.connect('delete-event',self.q.delete_event)
			self.w.add(self.q)
			(w,h) = self.q.qb.vb.size_request()
			(w3,h3) = self.q.qb.q.size_request()

			self.w.set_geometry_hints(min_width=max(w+w3+50,800),min_height=700)
			self.w.connect('delete-event',self.window_delete)

	def window_delete(self,w,e):
		self.q = None
		self.w = None

	def select_queue(self,b):
		self.master.jsonProxy.setValue('SEL',self.qname + '_enabled',self.selbox.get_active())
	
	def view(self,b):
		self.window_create()
		self.w.show_all()

	def edit(self,b):
		self.window_create()
		self.w.show_all()

class AutomaticLabel(uiwindow.Value):
	def __init__(self, master, table, row):
		uiwindow.Value.__init__(self, master)
		master.addValue('SEL', 'last_queue', self)
		master.addValue('SEL', 'queue_only', self)

		l = gtk.Label(_('<span size="x-large">Automatic selector</span>'))
		l.set_use_markup(True)
		l.set_alignment(0,0.5)

		self.le = gtk.EventBox()
		self.le.basecolor = self.le.style.bg[gtk.STATE_NORMAL]
		self.le.add(l)

		table.attach(self.le,0,1,row,row+1,yoptions=gtk.FILL,xpadding=5)

		# pack automatic selector
		self.alls = gtk.CheckButton(label=_('enabled'))
		self.alls.connect('clicked',self.select_auto)
		# attach autonmous selector, without edit button
		table.attach(self.alls,2,3,row,row+1,gtk.FILL,gtk.FILL,xpadding=15)

	def select_auto(self,b):
		if b.get_active():
			self.master.jsonProxy.setValue('SEL','queue_only',False)
		else:
			self.master.jsonProxy.setValue('SEL','queue_only',True)

	def set_rts2(self, varname, value):
		if varname == 'SEL.last_queue':
			self.le.modify_bg(gtk.STATE_NORMAL,value[1] == 0 and gtk.gdk.Color('green') or self.le.basecolor)
		elif varname == 'SEL.queue_only':
			self.alls.set_active(not(value[1]))
		else:
			print 'unknow value (AutomaticLabel)', varname, value

class NextLabel(gtk.HBox, uiwindow.Value):
	def __init__(self, master):
		gtk.HBox.__init__(self)
		uiwindow.Value.__init__(self, master)

		self.tl = targets.TargetLabel (None, colorBellow=True, invalidText='<span size="x-large">System idle</span>')
		self.pack_start(self.tl,True)

		master.addValue('SEL', 'next_id', self)
	
	def set_rts2(self, varname, value):
		if value[1] is None or value[1] < 0:
			self.tl.id = None
		else:
			self.tl.id = value[1]
		self.tl.reload()

class Queues(rts2.Queues, uiwindow.UIFrame):
	def __init__(self, jsonProxy, dont_disable=False):
		uiwindow.UIFrame.__init__(self, jsonProxy, None)
		rts2.Queues.__init__(self, jsonProxy)

		self.vb = gtk.VBox()

		self.xmlCatDir = "/home/observer/RTS2-F/QUEUES/"
		#self.autosave_dir = '/home/observer/RTS2-F/QUEUES/autosave'
		self.autosave_dir = None

		self.action_area = gtk.HButtonBox()

		load = gtk.Button()
		load.set_image(gtk.image_new_from_stock(gtk.STOCK_OPEN,gtk.ICON_SIZE_MENU))
		load.connect('clicked',self.loadQueues)
		load.set_tooltip_markup(_('Load all queues from file'))
		self.action_area.add(load)

		save = gtk.Button()
		save.set_image(gtk.image_new_from_stock(gtk.STOCK_SAVE_AS,gtk.ICON_SIZE_MENU))
		save.set_tooltip_markup(_('Save all queues to file'))
		save.connect('clicked',self.saveQueues)
		self.action_area.add(save)

		shown = gtk.Button(label=_('Nightlog'))
		shown.connect('clicked',self.shownight)
		shown.set_tooltip_markup(_('Show night log'))
		self.action_area.add(shown)

		sb = gtk.Button(label=_('Simulate'))
		sb.connect('clicked',self.simulate)
		sb.set_tooltip_markup(_('Simulates what will be observed current or next night'))
		self.action_area.add(sb)

		eb = gtk.Button(label=_('Exit'))
		eb.connect('clicked',lambda x:gtk.main_quit())
		self.action_area.add(eb)

		self.connect('delete-event',self.delete_event)

		# get list of queue names
		try:
			self.load()
			qn = self.jsonProxy.getValue('SEL','queue_names')
		except KeyError,ke:
			import traceback
			traceback.print_exc()
			msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK,message_format=_('Cannot retrieve selector queues. Is selector running and configured with at least one queue?'))
			msgbox.run()
			raise ke

		self.nextl = NextLabel(self)
		self.vb.pack_start(self.nextl,False,False)

		self.table = gtk.Table(2*len(qn) + 4,4)
		self.table.set_col_spacings(5)
		self.table.set_row_spacings(10)

		self.sctable = gtk.ScrolledWindow()
		self.sctable.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

		self.sctable.add_with_viewport(self.table)

		# index of the current row filled in table
		qi = 0

		# simul queue is special..
		self.simulQueue = None
		if 'simul' in qn:
			self.simulQueue = Queue(self, 'simul', self.table, 0, label='Simulator')
			qn.remove('simul')
			qi += 2

		self.table.attach(gtk.HSeparator(),0,4,qi,qi+1,yoptions=gtk.FILL)
		qi += 1
		
		l = gtk.Label(_('<span size="x-large">Queues</span>'))
		l.set_use_markup(True)
		l.set_alignment(0,0.5)
		self.table.attach(l,0,4,qi,qi+1,yoptions=gtk.FILL)

		qi += 1
		self.table.attach(gtk.HSeparator(),0,4,qi,qi+1,yoptions=gtk.FILL)
		qi += 1

		self.qlabels = []

		for i in range(0,len(qn)):
		  	x = qn[i]
			self.qlabels.append(Queue(self, x, self.table, qi, index=(i + 1), dont_disable=dont_disable))
			qi += 2

		self.table.attach(gtk.HSeparator(),0,4,qi,qi+1,yoptions=gtk.FILL)
		qi += 1

		l = gtk.Label(_('<span size="x-large">Automatic selector</span>'))
		l.set_use_markup(True)
		l.set_alignment(0,0.5)

		AutomaticLabel(self, self.table, qi)

		self.vb.pack_start(self.sctable)

		vbox = gtk.VBox(False)
		vbox.pack_start(self.vb, True, True)
		vbox.pack_end(self.action_area, False, False)

		self.add(vbox)

	def show_queues(self):	
		self.show_all()

		(w1,h1) = self.table.size_request()
		(w2,h2) = self.action_area.size_request()
		(w3,h3) = self.nextl.size_request()

		self.set_size_request(max(w1,w2) + self.sctable.get_vscrollbar().size_request()[0] + 20,h1 + h2 + h3 + self.sctable.get_hscrollbar().size_request()[1] + 20)

	def loadQueues(self,b):
		d = gtk.FileChooserDialog(title=_('Load from file'),buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK),action=gtk.FILE_CHOOSER_ACTION_OPEN)
		d.set_default_response(gtk.RESPONSE_OK)
		d.set_geometry_hints(min_width=600,min_height=600)

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		d.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('Queues (*.ques)')
		fil.add_pattern('*.ques')
		d.add_filter(fil)
		
		d.set_filter(d.list_filters()[1])

		if self.xmlCatDir:
			d.set_current_folder(self.xmlCatDir)

		res = d.run()
		if res == gtk.RESPONSE_OK:
		  	self.load_xml(d.get_filename())
			self.xmlCatDir = d.get_current_folder()
			# ask user if changes should be saved..
			msgbox = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO,message_format=_('Save to server?'))
			msgbox.format_secondary_markup(_('Do you want to save loaded queues to server? You probably would like do this, but please understand that <b>answering yes will replace current queues on the server.</b>'))
			if msgbox.run() == gtk.RESPONSE_YES:
				self.save()
			msgbox.destroy()
		d.destroy()

	def delete_event(self,w,e):
		if self.autosave_dir is not None:
			self.saveQueuesToFile('{0}/{1}'.format(self.autosave_dir,time.strftime('%Y.%m%d-%H:%M:%S_auto.ques',time.localtime())))
		return False
	
	def saveQueues(self,b):
		d = gtk.FileChooserDialog(title=_('Save to file'),buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK),action=gtk.FILE_CHOOSER_ACTION_SAVE)
		d.set_default_response(gtk.RESPONSE_OK)
		d.set_geometry_hints(min_width=600,min_height=600)

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		d.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('Queues (*.ques)')
		fil.add_pattern('*.ques')
		d.add_filter(fil)
		
		d.set_filter(d.list_filters()[1])

		if self.xmlCatDir:
			d.set_current_folder(self.xmlCatDir)

		d.set_current_name('queues.ques')

		d.set_do_overwrite_confirmation(True)

		res = d.run()
		if res == gtk.RESPONSE_OK:
			self.save_xml(d.get_filename())
			self.xmlCatDir = d.get_current_folder()
		d.destroy()

	def shownight(self, b):
		def __show(self):
			night = nights.NightDialog()
			gobject.idle_add(night.show)
		self.jsonProxy.queue(__show, _('Shwing night logs'), self)

	def simulate(self,b=None):
		ns = self.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
		ne = self.jsonProxy.getValue('centrald', 'night_ending')
		if ns > ne:
			ns = time.time()
		print "simulate {0} {1}".format(ns,ne)
		self.jsonProxy.executeCommand('SEL','simulate {0} {1}'.format(ns,ne))
