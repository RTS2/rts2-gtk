#!/usr/bin/env python
#
# Queue frame - to fill queue
#
# Petr Kubanek <petr@kubanek.net>

import gtk
import gobject
import gettext
import login
import string
import calendar
import time
import target
import targets
import timewidget
import nights
import fuzzytime
import xml.dom.minidom
import importcatalog
import threading
import rts2.json
import rts2.queue
import uiwindow

QUEUE_FIFO                   = 0
QUEUE_CIRCULAR               = 1
QUEUE_HIGHEST                = 2
QUEUE_WESTEAST               = 3
QUEUE_WESTEAST_MERIDIAN      = 4
QUEUE_SET_TIMES              = 5

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

def nighttime(t):
	if t is None:
		return '----'
	return time.strftime('%x %X %Z',time.localtime(t))

class TimeDialog(gtk.Dialog):
	"""Window to select time.
	"""
	def __init__(self, title, parent, b, callback):
		gtk.Dialog.__init__(self, title, parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)

		self.__callback = callback
		self.button = b

		self.date = gtk.Calendar()
		self.vbox.pack_start(self.date, False, False)

		self.time = timewidget.TimeWidget(_('Time:'))

		self.vbox.pack_start(self.time, False, False)

		self.add_button(_('C_lear'), 10)
		self.add_button(_('_Tonight'), 11)
		self.add_button(_('_Set'), 12)
		self.add_button(_('_Cancel'), 13)

		self.load_time(b.get_time())

		self.connect('response', self.response)

		self.date.grab_focus()
		self.show_all()
	
	def load_time(self, stime):
		lt = time.localtime(stime)
		self.date.select_month(lt[1] - 1,lt[0])
		self.date.select_day(lt[2])

		self.time.set_time(lt[3], lt[4], lt[5])

	def response(self, dialog, response_id):
		if response_id == 10:
			self.button.set_time(None)
			self.__callback(None)
			self.destroy()
		elif response_id == 11:
			lt = time.localtime()
			self.date.select_month(lt[1] - 1,lt[0])
			self.date.select_day(lt[2])
		elif response_id == 12:
			d = self.date.get_date()
			d = (d[0], d[1]+1, d[2], self.time.get_hours(), self.time.get_minutes(), self.time.get_seconds(), -1, -1, -1)
			t = time.mktime(d)
			if t is not None and t < time.time():
				msg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Specified time is in past. Please specify time in future'), buttons=gtk.BUTTONS_OK)
				msg.run()
				msg.destroy()
			else:
				if self.__callback(t):
					self.destroy()
		else:
			self.destroy()

class TimeButton(gtk.Button):
	def __init__(self, t):
		gtk.Button.__init__(self)
		self.set_time(t)

	def set_time(self,t):
		self.__t = t
		self.set_label(nighttime(self.__t))

	def get_time(self):
		return self.__t

class TimeEntry(gtk.HBox):
	"""Class for displaying clickable times"""
	def __init__(self, jsonProxy, queueEntry):
		gtk.HBox.__init__(self)
		self.jsonProxy = jsonProxy
		self.__queueEntry = queueEntry

		def spacer():
			sp = gtk.Label()
			sp.set_size_request(6,0)
			return sp

		self.pack_start(spacer(),False,False)
		self.pack_start(gtk.Label(_('from')),False,False)
		self.pack_start(spacer(),False,False)
		self.start_b = TimeButton(self.__queueEntry.get_start())
		self.start_b.connect('clicked', self.change_time, self.__queueEntry.set_start)
		self.pack_start(self.start_b,False,False)

		self.pack_start(spacer(),False,False)
		self.pack_start(gtk.Label(_('to')),False,False)
		self.pack_start(spacer(),False,False)
		self.end_b = TimeButton(self.__queueEntry.get_end())
		self.end_b.connect('clicked', self.change_time, self.__queueEntry.set_end)
		self.pack_start(self.end_b,False,False)

	def change_time(self, b, callback):
		dw = None
		if b == self.start_b:
			dw = TimeDialog(_('Set start time'), self.get_toplevel(), self.start_b, callback)
		else:
			dw = TimeDialog(_('Set end time'), self.get_toplevel(), self.end_b, callback)
		dw.run()

	def set_start(self, start):
		self.start_b.set_time(start)

	def set_end(self, end):
		self.end_b.set_time(end)

class QueueEntry(rts2.queue.QueueEntry):
	"""Display and manage queue entry."""
	def __init__(self, jsonProxy, id, start, end, qid, expected_start=None, nsto=None, readonly=False):
		self.te = None
		self.te_box = gtk.VBox()
		self.te_signal = None
		self.nsto = nsto
		self.readonly = readonly

		rts2.queue.QueueEntry.__init__(self, jsonProxy, id, start, end, qid)

		self.expectedStartTime = gtk.Label()
		self.expectedStartTime.set_alignment(0, 0.5)

		# button box
		self.bb = gtk.HBox()

		self.expected_start = expected_start
		self.targetLabel = targets.TargetLabel(id, self.expected_start, colorBellow=True)
		self.violated = None

		self.tb = gtk.ToggleButton('T')
		self.tb.set_tooltip_markup(_('Show and set, or delete time entry. Start time provides lower limit for observation start time, end time prowiders upper limit on observation time. Please be aware that number of observations the target script will run is primary determined by "Remove executed" option.'))
		self.bb.add(self.tb)

		if not(self.readonly):
			self.top = gtk.Button()
			self.top.set_image(gtk.image_new_from_stock(gtk.STOCK_GOTO_TOP,gtk.ICON_SIZE_MENU))
			self.bb.add(self.top)

			self.up = gtk.Button()
			self.up.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_UP,gtk.ICON_SIZE_MENU))
			self.bb.add(self.up)

			self.down = gtk.Button()
			self.down.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
			self.bb.add(self.down)

		self.ib = gtk.Button()
		self.ib.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
		self.ib.connect('clicked', self.target_info)
		self.bb.add(self.ib)

		if not(self.readonly):
			self.dele = gtk.Button()
			self.dele.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
			self.bb.add(self.dele)

		self.durbox = gtk.EventBox()
		self.dur = gtk.Label()
		self.dur.set_alignment(1, 0.5)
		self.durbox.add(self.dur)

	def reload(self, expected_start, nsto):
		self.expected_start = expected_start
		self.targetLabel.set_id(self.id, self.expected_start)
		self.set_expected_start_time(self.expected_start)
		self.dur.set_markup('<b>{0}</b>  '.format(fuzzytime.fuzzy_delta(self.duration())))
		self.durbox.modify_bg(gtk.STATE_NORMAL, self.targetLabel.color)
		# sets violated + its label
		if len(self.targetLabel.violated) > 0:
			if self.violated is None:
				self.violated = gtk.TextView()
				self.violated.set_wrap_mode(gtk.WRAP_WORD)
				self.violated.set_editable(False)
				self.violated.set_cursor_visible(False)
				self.te_box.pack_start(self.violated)
			vt = ""
			for x in self.targetLabel.violated:
				# load when it is violated
				try:
					if expected_start > nsto:
						nsto = expected_start
					viol = self.jsonProxy.loadJson('/api/violated',{'id':self.targetLabel.id, 'consts':x, 'from':expected_start, 'to':nsto})
					if len(viol[x]) == 0:
						continue
					vt += '\n  ' + x + ' '
					if viol[x][0] == expected_start - 3600:
						vt += string.join(map(lambda y:'<{0} - {1}'.format(nighttime(y[0]), nighttime(y[1])), viol[x]),' ')
					else:
						vt += string.join(map(lambda y:'{0} - {1}'.format(nighttime(y[0]), nighttime(y[1])), viol[x]),' ')
				except Exception,ex:
					import traceback
					traceback.print_exc()
					vt += str(ex)
			self.violated_b = gtk.TextBuffer()
			self.violated_b.set_text(_('Violate:{0}').format(vt))
			self.violated.set_buffer(self.violated_b)
		elif self.violated is not None:
			self.remove(self.violated)
			self.violated = None

	def attach(self, table, i, readonly):
		"""Attach QueueEntry to table, display it"""

		table.attach(self.expectedStartTime, 0, 1, i,i+1, gtk.SHRINK, 0, 5)
		table.attach(self.targetLabel, 1, 2, i, i+1, gtk.FILL|gtk.EXPAND|gtk.SHRINK, 0)
		table.attach(self.durbox, 2, 3, i, i+1, gtk.SHRINK, 0)

		if readonly:
			self.bb = gtk.HBox()
			#self.bb.add(self.tb)
			#self.bb.add(self.ib)
			#self.bb.show_all()

		table.attach(self.bb, 3, 4, i, i+1, gtk.SHRINK, 0)

		if self.te_signal is None:
			self.te_signal = self.tb.connect('toggled', table.time_clicked, self)

		table.attach(self.te_box,1,4,i+1,i+2,gtk.FILL|gtk.EXPAND|gtk.SHRINK,gtk.SHRINK)

		if (not(self.get_start() is None and self.get_end() is None)):
			self.tb.set_active(True)
			self.show_te()
		else:
			self.tb.set_active(False)

	def target_info(self,b):
		def __call(self):
			gobject.idle_add(target.TargetDialog(self.id).show)
		self.jsonProxy.queue(__call, _('Calling target info'), self)
	
	def setColorViolated(self,testConstraint):
		self.targetLabel.setColorViolated(testConstraint)

	def timeedit(self, b=None):
		if self.te is None:
			self.show_te()
		else:
			self.te_box.remove(self.te)
			self.te = None

	def show_te(self):
		if self.te is None:
			self.te = TimeEntry(self.jsonProxy, self)
			self.te_box.pack_end(self.te, False, False)
		self.te.set_start(self.get_start())
		self.te.set_end(self.get_end())

	def showtimes(self,show):
		"""Show/hides times"""
		self.tb.set_active(show)

	def duration(self,nextEl=None):
		if not(self.get_start() is None and self.get_end() is None):
			fr = self.get_start()
			en = self.get_end()
			if en is None and nextEl is not None:
				en = nextEl.get_start()
			if fr is not None and en is not None:
				if en > fr:
					return en - fr
				return 0
		return self.targetLabel.duration()

	def set_start(self, start, check=True):
		if not self.readonly and check and start is not None and self.nsto is not None:
			e = self.get_end()
			if e is None:
				e = self.nsto
			if e < start:
				e = self.jsonProxy.loadJson('/api/night',{'day':start})['to']
			satisfied = self.jsonProxy.loadJson('/api/satisfied',{'id':self.get_target().id,'from':int(start),'to':int(e)})['satisfied']
			if len(satisfied) == 0:
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Target {0} cannot be observed from {1} to {2}.'.format(self.get_target().name, nighttime(start), nighttime(e))), buttons=gtk.BUTTONS_OK)
				msgbox.run()
				msgbox.destroy()
				return False
			elif satisfied[0][0] > start:
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Target {0} cannot be observed from {1}, adjusting start time to {2}.'.format(self.target.name, nighttime(start), nighttime(satisfied[0][0]))), buttons=gtk.BUTTONS_OK)
				msgbox.run()
				msgbox.destroy()
				start = satisfied[0][0]

		rts2.queue.QueueEntry.set_start(self, start)
		if start is not None:
			self.show_te()
		return True

	def set_end(self, end, check=True):
		if not self.readonly and check and end is not None and self.get_start() is not None:
			satisfied = self.jsonProxy.loadJson('/api/satisfied',{'id':self.get_target().id,'from':int(self.get_start()),'to':int(end)})['satisfied']
			if len(satisfied) == 0:
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Target {0} cannot be observed from {1} to {2}.'.format(self.get_target().name, nighttime(self.get_start()), nighttime(end))), buttons=gtk.BUTTONS_OK)
				msgbox.run()
				msgbox.destroy()
				return False
			elif satisfied[0][1] < end:
				end = satisfied[0][1]
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Target {0} cannot be observed until {1}, adjusting end time to {2}.'.format(self.get_target().name, nighttime(self.get_start()), nighttime(end))), buttons=gtk.BUTTONS_OK)
				msgbox.run()
				msgbox.destroy()

		rts2.queue.QueueEntry.set_end(self, end)
		if end is not None:
			self.show_te()
		return True

	def set_expected_start_time(self,s):
		self.targetLabel.start = s
		self.expectedStartTime.set_text(nighttime(s))

class SimulQueueEntry(QueueEntry):
	"""Display and manage queue entry."""
	def __init__(self, jsonProxy, id, start, end, qid, expected_start=None, nsto=None, readonly=True):
		QueueEntry.__init__(self, jsonProxy, id, start, end, qid, expected_start, nsto, readonly)

class QueueTable(gtk.Table, uiwindow.Value):
	"""Queue class. In entries hold QueueEntry object, and attach them to class. If entries are changed,
	table is deleted and build again from entries."""
	def __init__(self, master, qname, readonly):
		gtk.Table.__init__(self, 1, 4, False)
		uiwindow.Value.__init__(self, master)

		self.master.addValue('SEL', qname + '_ids', self)
		self.master.addValue('SEL', qname + '_start', self)
		self.master.addValue('SEL', qname + '_end', self)
		self.master.addValue('SEL', qname + '_qid', self)

		self.nsta = self.nsto = None

		self.readonly = readonly

		if self.readonly:
			self.queue = rts2.queue.Queue(self.master.jsonProxy, qname, queueType=SimulQueueEntry)
		else:
			self.queue = rts2.queue.Queue(self.master.jsonProxy, qname, queueType=QueueEntry)
		self.queue.load()
		self.__changed = False

		self.testconstr = True
		self.dont_ask_for_overrun = False
	
	def __changed_qid(self, value):
		# only delete qids which disappered
		changed = False
		last_ei = 0

		while last_ei < len(self.queue.entries):
			e = self.queue.entries[last_ei]
			if e.qid > 0:
				try:
					value[1].index(e.qid)
					last_ei += 1
				except ValueError,ve:
					self.queue.entries.remove(e)
					changed = True
			else:
				last_ei += 1
		
		# look for new order and new QUIDs
		last_ei = 0
		last_qi = 0
		for qid in value[1]:
			# find in entries next entry with quid
			while last_ei < len(self.queue.entries) and self.queue.entries[last_ei].qid < 0:
				last_ei += 1
			# if the algorithm hit end in entries queue, add new items to the end
			if last_ei >= len(self.queue.entries):
				try:
					e = QueueEntry(self.master.jsonProxy,
						self.master.jsonProxy.getValue('SEL', self.queue.name + '_ids')[last_qi],
						self.master.jsonProxy.getValue('SEL', self.queue.name + '_start')[last_qi],
						self.master.jsonProxy.getValue('SEL', self.queue.name + '_end')[last_qi],
						qid, -1, self.nsto, self.readonly)
					if e.get_start() is None:
						e.reload(self.nsta, self.nsto)
					else:	
						e.reload(e.get_start(), self.nsto)
					self.connectQueueEntry(e)
					self.queue.entries.append(e)
					changed = True
				except IndexError, ie:
					import traceback
					print 'Error in last qi', last_qi, last_ei, len(value[1]), qid, self.master.jsonProxy.getValue('SEL', self.queue.name + '_ids'), self.master.jsonProxy.getValue('SEL', self.queue.name + '_start'), self.master.jsonProxy.getValue('SEL', self.queue.name + '_end')
					traceback.print_exc()
			# there is target with qid. If it is the same, just continue
			elif not(self.queue.entries[last_ei].qid == qid):
				# order was changed. Next quids will be overwitten correctly, don't worry too much about them
				self.queue.entries[last_ei].target = None
				self.queue.entries[last_ei].set_start(self.master.jsonProxy.getValue('SEL', self.queue.name + '_start')[last_qi])
				self.queue.entries[last_ei].set_end(self.master.jsonProxy.getValue('SEL', self.queue.name + '_end')[last_qi])
				self.queue.entries[last_ei].id = self.master.jsonProxy.getValue('SEL', self.queue.name + '_ids')[last_qi]
				self.queue.entries[last_ei].qid = qid
				changed = True
			last_qi += 1
			last_ei += 1

		if changed:
			self.fillTable()

	def set_rts2(self, varname, value):
		if varname == 'SEL.' + self.queue.name + '_qid':
			self.master.jsonProxy.queue(self.__changed_qid, _('Updating queue'), value)

	def loadSel(self):
		self.master.jsonProxy.show_progress_dialog(self.get_toplevel())
	  	self.nsta = self.master.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
		self.nsto = self.master.jsonProxy.getValue('centrald', 'night_ending')
		self.expected_start = time.time()
		if self.nsta < self.nsto:
			self.expected_start = self.nsta

		self.queue.load()

		for e in self.queue.entries:
			def __load(self, e):
			  	if e.get_start() is not None:
					self.expected_start = e.get_start()
				e.reload(self.expected_start, self.nsto)
				self.connectQueueEntry(e)
				self.expected_start += e.duration()
			self.master.jsonProxy.queue(__load, _('Loading target {0}').format(e.id), self, e)

		self.recalculate_table()
		self.master.jsonProxy.queue(self.set_changed, _('Setting change'), False)
	
	def fillTable(self):
		def __fillTable(self):
			# empty table
			gobject.idle_add(self.foreach, self.remove)
			for i in range(0,len(self.queue.entries)):
				gobject.idle_add(self.queue.entries[i].attach, self, i*2, self.readonly)
			gobject.idle_add(self.show_all)

		self.master.jsonProxy.queue(__fillTable, _('Filling table'), self)

	def recalculate_table(self):
		def __recalculate(self):
		  	self.nsta = self.master.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
			self.nsto = self.master.jsonProxy.getValue('centrald', 'night_ending')
			self.expected_start = time.time()
			if self.nsta < self.nsto:
				self.expected_start = self.nsta

			for qe in self.queue.entries:
			  	if qe.get_start() is not None:
					self.expected_start = qe.get_start()
				qe.set_expected_start_time(self.expected_start)
				self.expected_start += qe.duration()

		self.master.jsonProxy.queue(__recalculate, _('Recalculating table'), self)

		# update table
		self.fillTable()

	def gui_clear(self):
		if len(self.queue.entries) > 0:
			self.set_changed(True)
		gobject.idle_add(self.foreach, self.remove)
		self.queue.entries = []

	def time_clicked(self, b, qe):
		qe.timeedit(b)
		self.show_all()
	
	def showtimes(self,show):
		map(lambda x:x.showtimes(show),self.queue.entries)	
	
	def reload(self):
		self.gui_clear()
		self.master.jsonProxy.queue(self.loadSel, _('Loading targets'))

	def setTestConstraint(self,testConstraint):
		self.testconstr = testConstraint
		map(lambda x:x.setColorViolated(testConstraint),self.queue.entries)

	def addEntry(self,id,start,end,recordchanges=True,queing=None):
		if queing is None:
			queing = self.queue.queueing
		if queing == QUEUE_FIFO and self.testconstr == True:
			name = 'not loaded'
			try:
				name = self.master.jsonProxy.loadJson('/api/tbyid',{'id':id})['d'][0][1] + ' (#{0})'.format(id)
				s = self.expected_start
				e = self.nsto
			except Exception,ex:
				s = e = 1
				pass
			if s < e:
				# find first possible time..
				satisfied = self.master.jsonProxy.loadJson('/api/satisfied',{'id':id,'from':int(s),'to':int(e)})['satisfied']
				if len(satisfied) == 0:
					try:
						gtk.gdk.threads_enter()
						msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, parent=self.get_toplevel(), flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Target {0} cannot be observed from {1} to {2}.'.format(name,nighttime(s),nighttime(e))))
						msgbox.add_button(_('Add anyway'),1)
						msgbox.add_button(_('Skip it'),2)
						ret = msgbox.run()
						msgbox.destroy()
						if ret == 2:
							return
					finally:
						gtk.gdk.threads_leave()

				elif satisfied[0][0] > s:
					try:
						gtk.gdk.threads_enter()
						msgbox = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, parent=self.get_toplevel(), flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_YES_NO, message_format=_('Target {0} is observable from {1} to {2}. Would you like to switch its start time to {1}?').format(name,nighttime(satisfied[0][0]),nighttime(satisfied[0][1])))
						if msgbox.run() == gtk.RESPONSE_YES:
							start = satisfied[0][0]
							self.expected_start = start
						msgbox.destroy()
					finally:
						gtk.gdk.threads_leave()
			else:
				if not(self.dont_ask_for_overrun):
					try:
						gtk.gdk.threads_enter()
						msgbox = gtk.MessageDialog(type=gtk.MESSAGE_WARNING, parent=self.get_toplevel(), flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, buttons=gtk.BUTTONS_OK, message_format=_('You have in queue targets with total duration longer than what is left from the current night. Target {0} will be added, but it is unlikely it will be observed').format(name))
						msgbox.add_button(_("Don't ask again"),1)
						if msgbox.run() == 1:
							self.dont_ask_for_overrun = True
						msgbox.destroy()
					finally:
						gtk.gdk.threads_leave()

		e = self.addEntryNoCheck(id,start,end,-1,recordchanges,self.expected_start)
		self.expected_start += e.duration()
		self.recalculate_table()

	def connectQueueEntry(self,e):
		e.nsto = self.nsto
		if not(self.readonly):
			e.top.connect('clicked',lambda x:self.top(e))
			e.up.connect('clicked',lambda x:self.up(e))
			e.down.connect('clicked',lambda x:self.down(e))
			e.dele.connect('clicked',lambda x:self.dele(e))

	def addEntryNoCheck(self,id,start,end,qid,recordchanges,expected_start):
		"""Add entry to entries. Return new entry."""
	  	if self.nsta is None:
			self.nsta = self.master.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
			self.nsto = self.master.jsonProxy.getValue('centrald', 'night_ending')

		e = QueueEntry(self.master.jsonProxy, id, start, end, qid, expected_start, self.nsto, self.readonly)
		if start is None:
			start = self.nsta
			if start < time.time():
				start = time.time()
			start += self.totalDuration()	

		e.reload(start, self.nsto)
		self.connectQueueEntry(e)
		self.queue.entries.append(e)
		if recordchanges:
			gobject.idle_add(self.set_changed, True)
		return e

	def dele(self, x):
		self.queue.entries.remove(x)
		self.recalculate_table()
		self.set_changed(True)
	
	def up(self, x):
		i = self.queue.entries.index(x)
		try:
			self.queue.entries[i-1],self.queue.entries[i] = self.queue.entries[i],self.queue.entries[i-1]
			self.recalculate_table()
			self.set_changed(True)
		except KeyError,ke:
			print "up",ke

	def down(self, x):
		i = self.queue.entries.index(x)
		try:
			self.queue.entries[i],self.queue.entries[i+1] = self.queue.entries[i+1],self.queue.entries[i]
			self.recalculate_table()
			self.set_changed(True)
		except KeyError,ke:
			print "down",ke

	def top(self,x):
		if len(self.queue.entries) > 1:
			self.queue.entries.remove(x)
			self.queue.entries.insert(0,x)
			self.recalculate_table()
			self.set_changed(True)	

	def entriesId(self):
		return map(lambda x:x.id,self.queue.entries)
	
	def totalDuration(self):
		dur = 0
		last = None
		qe = None
		for qe in self.queue.entries:
			if last is not(None):
				dur += last.duration(qe)
			last = qe
		if last is not None:
			dur += last.duration()
		return dur

	def set_changed(self, changed):
		self.__changed=changed
		if self.get_toplevel() is not None:
			def __changed(self):
				addt = ""
				if self.__changed:
					addt = " *"
				if self.get_toplevel().flags() & gtk.TOPLEVEL:	
					self.get_toplevel().set_title(_('Queue {0}{1}').format(self.queue.name,addt))

			gobject.idle_add(__changed, self)

	def was_changed(self):
		"""Return true if the queue was changed."""
		return self.__changed
	
	def from_xml(self,node):
		def __from_xml(self,node):
			self.gui_clear()
			self.queue.from_xml(node)

		  	self.nsta = self.master.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
			self.nsto = self.master.jsonProxy.getValue('centrald', 'night_ending')

			start = self.nsta
			if self.nsta < time.time():
				start = time.time()

			for e in self.queue.entries:
				e.reload(start, self.nsto)
				self.connectQueueEntry(e)
				e.targetLabel.set_id(e.id, start)
				start += e.duration()
		
			self.recalculate_table()
		self.master.jsonProxy.queue(__from_xml, _('Loading data from XML'), self, node)

class QueueType(gtk.VBox):
	def __init__(self,jsonProxy,qname):
		gtk.VBox.__init__(self)
		self.qname = qname
		gr = None
		self.queueing_b = []
		labels = [_('FIFO'),_('Circular'),_('Highest elevation'),_('West-east'), _('Meridian west-east'),_('First set first')]
		sel = jsonProxy.getValue('SEL',self.qname + '_queing')
		i = 0
		for l in labels:
			gr = gtk.RadioButton(group=gr,label=l)
			gr.num = i
			if sel == i:
				gr.set_active(True)
			self.pack_start(gr)
			self.queueing_b.append(gr)
			i += 1

	def get_index(self):
		for i in range(0,len(self.queueing_b)):
			if self.queueing_b[i].get_active():
				return i
		return -1

	def set_index(self,i):
		self.queueing_b[i].set_active(True)

class QueueBox(gtk.HBox, uiwindow.Value):
	def __init__(self,master,qname,load=True):
		gtk.HBox.__init__(self)
		uiwindow.Value.__init__(self,master)

		self.master = master
		self.set_homogeneous(False)
		self.qname = qname
		self.qscw = gtk.ScrolledWindow()
		self.qscw.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)

		# assign read-only flag
		try:
			self.readonly = not(master.jsonProxy.getVariable('SEL',self.qname + '_queing')[0] & rts2.json.RTS2_VALUE_WRITABLE)
			self.q = QueueTable(master,qname,self.readonly)
		except Exception,ex:
			msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=_('Cannot create queue: {0}'.format(str(ex))))
			msgbox.run()
			msgbox.destroy()
			import traceback
			traceback.print_exc(ex)

		# as this is after QueueTable call, rts2_set will be called after Queue is reloaded
		self.master.addValue('SEL', qname + '_qid', self)

		self.qscw.add_with_viewport(self.q)
		self.pack_start(self.qscw)

		self.d = None
		self.xmlCatDir = "/home/observer/RTS2-F/QUEUES/"

		self.vb = gtk.VBox()
		self.duration = gtk.Label()

		if load:
			self.reload()
		self.vb.pack_start(self.duration,False,False)

		relb = None

		if not(self.readonly):
			self.qtype = QueueType(master.jsonProxy,qname)
			self.vb.pack_start(self.qtype,False,False)

			self.timewindow = gtk.HBox()
			self.timewindow.pack_start(gtk.Label(_('Window:')), True, True)
			self.timeentry = timewidget.DigitsDisplay(gtk.Adjustment(0, 0, 100, 1, 10))
			self.timewindow.pack_start(self.timeentry, False, False)
			self.timewindow.pack_end(gtk.Label('m '), False, False)
			self.timewindow.set_tooltip_markup(_('Set window length in HH:MM:SS. Window length is important when a target in queue has specified start time. If window parameter is set, targets from queue(s) below this queue can be scheduled to fill up to start time + window length. This can reduce times when system switched to automatic selector as it runs out of targets.'))

			tv = self.master.jsonProxy.getValue('SEL', self.qname + '_window')
			if tv is None:
				tv = 0
			self.timeentry.set_value(tv / 60)

			self.checkskip = gtk.CheckButton(_('_Skip targets'))
			self.checkskip.set_tooltip_markup(_('Test is applied before each target is selected for observations. If unchecked, targets at the top of the queue that fail the constraints in the database are <b>removed</b> from the queue. If checked, targets at the top of the queue that fail the constraints are just moved to the end of the queue.'))
			self.checkskip.set_active(self.master.jsonProxy.getValue('SEL', self.qname + '_skip_below'))

			self.testconstr = gtk.CheckButton(_('_Test constraint'))
			self.testconstr.set_tooltip_markup(_('If unchecked, only the target visibility is tested before attempting an observation. If checked, targets that violate the constraints are considered to be below the horizon. If <i>Skip targets</i> is unchecked (checked), the target is removed from (moved to the end of) the queue.'))
			self.testconstr.set_active(self.master.jsonProxy.getValue('SEL', self.qname + '_test_constr'))
			self.q.setTestConstraint(self.testconstr.get_active())
			self.testconstr.connect('toggled',lambda x:self.q.setTestConstraint(self.testconstr.get_active()))

			self.rexecuted = gtk.CheckButton(_('Remove observed'))
			self.rexecuted.set_tooltip_markup(_('Test is applied after each target is observed. If unchecked, targets remain in the queue, as long as they are optimal. For example, in <i>Highest elevation</i> mode, the target remains at the top of the queue as long as it has the highest elevation of all targets in the queue. Also, observations may be repeated as long as they do not violate constraints in the database. If unchecked, only a single observation will occur.'))
			self.rexecuted.set_active(self.master.jsonProxy.getValue('SEL',self.qname + '_remove_executed'))

			relb = gtk.Button(label=_('_Load from server'))
			relb.connect('clicked', self.reload)
		else:
			relb = gtk.Button(label=_('_Simulate'))
			relb.connect('clicked', self.simulate)

		self.addb = gtk.Button(label=_('_Add targets'))
		self.addb.connect('clicked', self.addTarget)

		addFile = gtk.Button(label=_('Add _catalog'))
		addFile.connect('clicked', self.addCatalogue)

		showTimes = gtk.Button(_('Show all times'))
		showTimes.connect('clicked', lambda b:self.q.showtimes(True))

		clear = gtk.Button(_('Clear'))
		clear.connect('clicked', lambda x:self.q.gui_clear())

		set = gtk.Button(label=_('_Save to server'))
		set.connect('clicked', self.execute)

		shown = gtk.Button(label=_('Nightlog'))
		shown.connect('clicked', self.shownight)

		saveXML = gtk.Button(label=_('Save to file'))
		saveXML.connect('clicked', self.saveToXML)

		loadXML = gtk.Button(label=_('Load from file'))
		loadXML.connect('clicked', self.loadFromXML)

		quit = gtk.Button(label=_('Done'))
		quit.connect('clicked',self.quit)

		self.vbb = gtk.VButtonBox()

		self.vbb.add(relb)

		if not(self.readonly):
			self.vbb.add(addFile)
			self.vbb.add(self.addb)
			self.vbb.add(showTimes)
			self.vbb.add(clear)
			self.vbb.add(set)

		self.vbb.add(shown)
		self.vbb.add(saveXML)

		if not(self.readonly):
			self.vbb.add(loadXML)

		self.vbb.add(quit)

		self.vb.pack_end(self.vbb, False, False)

		if not(self.readonly):
			self.vb.pack_end(self.rexecuted, False, False)
			self.vb.pack_end(self.testconstr, False, False)
			self.vb.pack_end(self.checkskip, False, False)
		  	self.vb.pack_end(self.timewindow, False, False)

		self.pack_end(self.vb, False, False)
		self.show_all()

	def set_rts2(self, varname, value):
		self.printDuration()

	def printDuration(self):
		def __printDuration(self):
			text = _('Total time {0}').format(fuzzytime.fuzzy_delta(self.q.totalDuration()))
			gobject.idle_add(self.duration.set_text, text)

		self.master.jsonProxy.queue(__printDuration, _('Calculating total duration'), self)

	def testChanged(self):
		if self.q.was_changed():
			msgbox = gtk.MessageDialog(type=gtk.MESSAGE_WARNING, message_format=_('You have unsaved queue changes. If you exit now, all changes will be lost.'))
			msgbox.add_button(_('Continue editing'),gtk.RESPONSE_CANCEL)
			msgbox.add_button(_('Exit anyway'),gtk.RESPONSE_OK)
			msgbox.add_button(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL)
			if msgbox.run() == gtk.RESPONSE_CANCEL:
				msgbox.destroy()
				return True
			msgbox.destroy()
		return False

	def force_reload(self,b=None,thread_started=False):
		def __reload(self):
			self.master.jsonProxy.refresh()
			self.q.gui_clear()
			self.q.loadSel()
			if not(self.readonly):
				self.set_from_queue()
			self.printDuration()

		self.master.jsonProxy.queue(__reload, _('Reloading queue'), self)

	def reload(self,b=None,thread_started=False):
		self.force_reload(thread_started=thread_started)

	def simulate(self,b=None):
		self.master.jsonProxy.refresh()
		ns = self.master.jsonProxy.getValue('centrald', 'night_beginning', refresh_not_found=True)
		ne = self.master.jsonProxy.getValue('centrald', 'night_ending')
		if ns > ne:
			ns = time.time()
		self.simul_start = ns
		self.simul_end = ne
		self.master.jsonProxy.executeCommand('SEL', 'simulate {0} {1}'.format(ns, ne))

	def addCatalogue(self,b):
		t = importcatalog.ImportAssistant()
		t.connect('close',self.loadCatalogue)

	def loadCatalogue(self, assistant):
		"""Load catalog from disk, put it to queue."""
		self.master.jsonProxy.show_progress_dialog(self.get_toplevel())

		def __addqueu(self,assistant):
			for x in assistant.created_targets_id:
				self.master.jsonProxy.queue(self.q.addEntry, _('Adding catalogue target {0}').format(x), x, None, None)
			gobject.idle_add(assistant.destroy)

		self.master.jsonProxy.queue(__addqueu, _('Loading catalogue'), self, assistant)
	
	def addTarget(self,b):
		if self.d is None:
			def __addTarget(self):
				self.master.jsonProxy.newConnection()

				self.q.dont_ask_for_overrun = False
			  	self.d = targets.SelectDialog(buttons=[(_('Add'),1),(_('Exit'),2)],selmode=gtk.SELECTION_MULTIPLE)
				self.d.connect('response', self.add_responded)
				gobject.idle_add(self.d.show)

			b.set_sensitive(False)
		
			self.master.jsonProxy.queue(__addTarget, _('Adding target'), self)	
	
	def add_responded(self,b,resp):
		if resp == 1:
			self.master.jsonProxy.show_progress_dialog(self.get_toplevel())

			for x in self.d.getSelected(0):
				self.master.jsonProxy.queue(self.q.addEntry, _('Adding target {0}').format(x), x, None, None, queing=self.qtype.get_index())
			self.printDuration()
		else:
			self.d.hide()
			self.d = None
			self.addb.set_sensitive(True)
	
	def check_queue_times(self):
		start = None
		i = 0
		last_entry = None
		last_i = None
		for e in self.q.queue.entries:
			if start is not None and e.get_start() is not None and e.get_start() < start:
				msg = gtk.MessageDialog(type=gtk.MESSAGE_WARNING, parent=self.get_toplevel(), flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, message_format=_('Start time of target {0} is before start time of target {1}. How you would like to reorder those targets?').format(e.get_target().name, last_entry.get_target().name))
				msg.add_button(_('Move {0} before {1}').format(e.get_target().name, last_entry.get_target().name), 1)
				msg.add_button(_('Move {0} after {1}').format(last_entry.get_target().name, e.get_target().name), 2)
				ret = msg.run()
				if ret == 1:
					self.q.queue.entries.remove(e)
					self.q.queue.entries.insert(last_i, e)
					e = last_entry
				elif ret == 2:
					self.q.queue.entries.remove(last_entry)
					self.q.queue.entries.insert(i, last_entry)
					e = last_entry
				msg.destroy()

			if e.get_start() is not None:
				last_entry = e
				last_i = i
				start = e.get_start()
			i += 1

	def save_queue(self):
		self.q.queue.window = self.timeentry.get_value_as_int() * 60

		self.q.queue.skip_below = self.checkskip.get_active()
		self.q.queue.test_constr = self.testconstr.get_active()
		self.q.queue.remove_executed = self.rexecuted.get_active()

		self.q.queue.queueing = self.qtype.get_index()

	def execute(self,b=None):
		def __execute(self):
			self.save_queue()

			self.q.queue.save(remove_new=True)
			self.q.set_changed(False)

		self.check_queue_times()
		self.master.jsonProxy.queue(__execute, _('Executing queue'), self)

	def shownight(self,b):
		night = nights.NightDialog()
		night.show ()
	
	def saveToXML(self,b):
		d = gtk.FileChooserDialog(title=_('Save to file'),buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK),action=gtk.FILE_CHOOSER_ACTION_SAVE)
		d.set_default_response(gtk.RESPONSE_OK)
		d.set_geometry_hints(min_width=600,min_height=600)

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		d.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('Queue (*.que)')
		fil.add_pattern('*.que')
		d.add_filter(fil)
		
		d.set_filter(d.list_filters()[1])

		if self.xmlCatDir:
			d.set_current_folder(self.xmlCatDir)

		d.set_current_name('queue.que')

		d.set_do_overwrite_confirmation(True)

		res = d.run()
		if res == gtk.RESPONSE_OK:
			document = self.getXMLDoc()
			f = open(d.get_filename(),'w')
			document.writexml(f,addindent='\t',newl='\n')
			f.close()
			self.xmlCatDir = d.get_current_folder()
		d.destroy()

	def getXMLDoc(self):
		document = xml.dom.minidom.getDOMImplementation().createDocument('http://rts2.org','queue',None)
		self.q.queue.to_xml(document,document.documentElement)
		return document
	
	def loadFromXML(self,b):
		if self.testChanged():
			return
		d = gtk.FileChooserDialog(title=_('Load from file'),buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK),action=gtk.FILE_CHOOSER_ACTION_OPEN)
		d.set_default_response(gtk.RESPONSE_OK)
		d.set_geometry_hints(min_width=600,min_height=600)

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		d.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('Queue (*.que)')
		fil.add_pattern('*.que')
		d.add_filter(fil)
		
		d.set_filter(d.list_filters()[1])

		if self.xmlCatDir:
			d.set_current_folder(self.xmlCatDir)

		res = d.run()
		if res == gtk.RESPONSE_OK:
		  	f = open(d.get_filename(),'r')
			document = xml.dom.minidom.parse(f)
			f.close()
			self.setXMLDoc(document.documentElement)
			self.xmlCatDir = d.get_current_folder()
		d.destroy()

	def setXMLDoc(self,node):
		self.q.gui_clear()
		self.q.from_xml(node)
		self.set_from_queue()

		self.jsonProxy.queue(self.q.set_changed, _('Setting change'), True)

	def set_from_queue(self):
		def __set_from_queue():
			if self.q.queue.window is None:
				self.timeentry.set_value(0)
			else:
				self.timeentry.set_value(self.q.queue.window / 60)

			self.checkskip.set_active(self.q.queue.skip_below)
			self.testconstr.set_active(self.q.queue.test_constr)
			self.rexecuted.set_active(self.q.queue.remove_executed)

			try:
				self.qtype.set_index(int(self.q.queue.queueing))
			except ValueError,er:
				pass

		self.master.jsonProxy.queue(__set_from_queue, _('Setting queue values'))

	def quit(self,b):
		"""Quit the queue."""
		if self.testChanged() == False:
			self.get_toplevel().hide()

class QueueFrame(gtk.Frame):
	def __init__(self,master,name):
		gtk.Frame.__init__(self)

		self.qb=QueueBox(master, name)
		self.vbox=gtk.VBox()
		self.vbox.pack_start(self.qb,True)
		self.add(self.vbox)

	def delete_event(self,w=None,e=None):
		if self.qb.testChanged():
			return True
		return self.get_toplevel().hide_on_delete()
			
if __name__ == '__main__':
	l = login.Login()
	l.signon(startQueue=True)

	queue = 'manual'

	master = uiwindow.UIFrame(login.getProxy(),queue)

	w = gtk.Window()
	w.set_title(_('Queue {0}'.format(queue)))
	w.connect('destroy',gtk.main_quit)
	w.add(master)

	master.add(QueueBox(master, queue))

	w.show_all()
	gtk.main()
