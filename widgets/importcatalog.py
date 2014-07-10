#!/usr/bin/env python
"""Guide user through importing catalog"""
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

import json
import jsontable
import gtk
import gettext
import gobject
import login
import time
import re
import radec
import rts2const

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class ImportAssistant(gtk.Assistant):
	"""Dailog to guide user through catalog import."""
	def __init__(self):
		gtk.Assistant.__init__(self)
		self.set_title(_('Import catalogue'))
		self.set_geometry_hints(min_width=800,min_height=600)

		self.connect('apply',self.apply_pressed)
		self.connect('cancel',self.cancel_pressed)
		self.connect('prepare',self.prepare)

		self.page0 = gtk.FileChooserWidget()

		fil = gtk.FileFilter()
		fil.set_name('All files (*)')
		fil.add_pattern('*')
		self.page0.add_filter(fil)

		fil = gtk.FileFilter()
		fil.set_name('FLOW catalogs (*.mctR)')
		fil.add_pattern('*.mctR')
		self.page0.add_filter(fil)

		self.page0.set_filter(self.page0.list_filters()[1])

		self.page0.set_current_folder('/home/observer/RTS2-F/CATALOGS/')

		self.append_page(self.page0)
		self.set_page_type(self.page0,gtk.ASSISTANT_PAGE_CONTENT)
		self.set_page_title(self.page0,_('Select catalog to import'))
		self.set_page_complete(self.page0,False)

		self.page0.connect('selection-changed',self.selection_activated)

		self.page_match = gtk.VBox()
		self.append_page(self.page_match)
		self.set_page_type(self.page_match,gtk.ASSISTANT_PAGE_CONTENT)
		self.set_page_title(self.page_match,_('Matching targets'))

		self.pm_l = gtk.Label()
		self.page_match.pack_start(self.pm_l,False,False)

		self.pm_t = gtk.ProgressBar()
		self.page_match.pack_start(self.pm_t,False,False)

		self.targetstore = jsontable.JsonTable(None,data={'h':[
			{"n":"Process","t":"b","c":0},
			{"n":"Create","t":"b","c":1},
			{"n":"Enable","t":"b","c":2},
			{"n":"Target Name","t":"s","c":3},
			{"n":"RA","t":"r","c":4},
			{"n":"DEC","t":"d","c":5},
			{"n":"ID","t":"n","prefix":"/targets/","href":0,"c":6},
			{"n":"Matched name","t":"s","c":7},
			{"n":"Matched RA","t":"r","c":8},
			{"n":"Matched DEC","t":"d","c":9},
			{"n":"Script","t":"s","c":10},
			{"n":"Object","t":"object","c":11}],
		"d":[]})

		self.targetstore.tv.get_column(0).get_cell_renderers()[0].set_property('activatable',True)
		self.targetstore.tv.get_column(0).get_cell_renderers()[0].connect('toggled',self.toggled_process)

		self.targetstore.tv.get_column(1).add_attribute(self.targetstore.tv.get_column(1).get_cell_renderers()[0],'activatable',0)
		self.targetstore.tv.get_column(1).get_cell_renderers()[0].connect('toggled',self.toggled_create)

		self.targetstore.tv.get_column(2).add_attribute(self.targetstore.tv.get_column(2).get_cell_renderers()[0],'activatable',0)
		self.targetstore.tv.get_column(2).get_cell_renderers()[0].connect('toggled',self.toggled_enabled)

		self.targetstore.tv.get_column(6).get_cell_renderers()[0].set_property('editable',True)
		self.targetstore.tv.get_column(6).get_cell_renderers()[0].connect('edited',self.match_edited)

		for i in range(1,self.targetstore.data.get_n_columns()-1):
			self.targetstore.tv.get_column(i).add_attribute(self.targetstore.tv.get_column(i).get_cell_renderers()[0],'sensitive',0)

		self.page_match.pack_end(self.targetstore,True,True)

		self.page_create_summary = gtk.ScrolledWindow()
		self.create_summary_text = gtk.TextView()

		self.page_create_summary.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
		self.page_create_summary.add(self.create_summary_text)

		self.append_page(self.page_create_summary)
		self.set_page_type(self.page_create_summary,gtk.ASSISTANT_PAGE_CONFIRM)
		self.set_page_title(self.page_create_summary,_('Summary'))

		self.page_create = gtk.ScrolledWindow()
		self.create_text = gtk.TextView()

		self.page_create.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
		self.page_create.add(self.create_text)

		self.append_page(self.page_create)
		self.set_page_type(self.page_create,gtk.ASSISTANT_PAGE_SUMMARY)
		self.set_page_title(self.page_create,_('Populating database'))

		self.pi = None
		self.program = None
		self.acqexp = 15

		# ID of created targets
		self.created_targets_id = []

		self.show_all()

	def toggled_process(self,cell,path):
		self.targetstore.data[path][0] = not self.targetstore.data[path][0]

	def toggled_create(self,cell,path):
		self.targetstore.data[path][1] = not self.targetstore.data[path][1]

	def toggled_enabled(self,cell,path):
		self.targetstore.data[path][2] = not self.targetstore.data[path][2]

	def match_edited(self,cellrenderertext,path,new_text):
		self.targetstore.data[path][6] = int(new_text)

	def apply_pressed(self,assistant):
		if self.get_current_page() == 1:
			gtk.main_quit()
	
	def cancel_pressed(self,assistant):
		self.hide()

	def parsePiProg(self,line):
		pi = re.match(r'^\!P.I.:\s*(\S.*)$', line)
		if pi:
			self.pi = pi.group(1)
			return
		program = re.match(r'^\!Program:\s*(\S.*)$', line)
		if program:
		  	self.program = program.group(1)
			return
		print >> sys.stderr, 'Unknow ! line: {0}'.format (line)
	
	def process_line(self):
		if not self.get_current_page() == 1:
			return False
		if len(self.lines) == 0:
		  	self.pm_l.set_text('Target matching completed')
			self.pm_t.set_fraction(1)
			self.set_page_complete(self.page_match,True)
			return False
		l = self.lines[0].rstrip()
		self.pm_l.set_text(l)
		self.pm_t.set_fraction(float(self.pm_tt-len(self.lines))/self.pm_tt)

		self.lines = self.lines[1:]

		# process line..
		if (len(l) == 0):
		  	return True
		if l[0] == '#' and len(l) > 1 and l[1] == '!':
		  	self.parsePiProg(l[1:])
			return True
		if l[0] == '!':
		  	self.parsePiProg(l)
			return True
		if l[0] == '#':
		  	return True

		a = l.split()
		if (a[2][0] != '-' and a[2][0] != '+'):
		  	a[2] = '+' + a[2]

		a[1] = radec.from_hms(a[1]) * 15.0
		a[2] = radec.from_hms(a[2])

		candidates = login.getProxy().loadJson('/api/tbyname',{'n':a[0],'pm':0})['d']
		if len(candidates) == 1:
			self.pm_l.set_text(_('Matched target {0} to ID {1} by name').format(a[0],candidates[0][0]))
		else:
			candidates = login.getProxy().loadJson('/api/tbydistance',{'ra':a[1],'dec':a[2],'radius':0.1})['d']
			if len(candidates) == 1:
				self.pm_l.set_text(_('Matched target {0} to {1} with ID {2} by coordinates').format(a[0],candidates[0][1],candidates[0][0]))
			else:
				candidates = None
		if candidates:
			self.addTarget(candidates[0][0],candidates[0][1],candidates[0][2],candidates[0][3],a)
		else:
			self.addTarget(None,None,None,None,a)
		return True


	def cl_append(self,msg,nl=True,intend=False):
		if intend:
			msg = '    ' + msg
		if nl:
			msg = msg + '\n'
		def __append(self,msg):
			self.active_text.get_buffer().insert(self.active_text.get_buffer().get_end_iter(), msg)
			self.active_text.scroll_to_iter(self.active_text.get_buffer().get_end_iter(), 0)
		gobject.idle_add(__append,self,msg)

	def parse_script(self,scr):
		ret = ''
		s = scr.split(',')
		for se in s:
		  	fil = se.split('-')
			ret += 'filter=' + fil[0] + ' '
			if (int(fil[2]) > 1):
				ret += 'for ' + fil[2] + ' { E ' + fil[1] + ' }'
			else:
			  	ret += 'E ' + fil[1]
			ret += ' '
		return ret

	def create_target(self, page, doit=True):
		"""Create a single target"""
		for create_row in range(0,len(self.targetstore.data)):
			if len(self.targetstore.data) == create_row:
				self.set_page_complete(page,True)
				return
			process,create_create,create_enabled,create_tar_id,create_a,tn,tid = self.targetstore.data.get(self.targetstore.data.get_iter(create_row),0,1,2,6,11,7,8)
			if not(process):
				self.cl_append(_('Skipping target {0}'.format(create_a[0])))
				continue
			if create_create:
				self.cl_append(_('Creating target {0}').format(create_a[0]))
				if doit:
					d=login.getProxy().loadJson('/api/create_target',{'tn':create_a[0],'ra':create_a[1],'dec':create_a[2]})
					create_tar_id = d['id']	
					self.cl_append(_('created with ID {0}').format(create_tar_id))
			else:
				# not creating non matched target - skip it..
				if create_tar_id <= 0:
					self.cl_append(_('Skipping target {0}').format(create_a[0]) + '\n')
				else:
					self.cl_append(_('Updating target {0} with ID {1}').format(tn,tid))
					if doit:
						d=login.getProxy().loadJson('/api/update_target',{'id':create_tar_id,'tn':create_a[0],'ra':create_a[1],'dec':create_a[2]})
			# create script
			self.cl_append(_('parsing script {0}').format(create_a[6]),intend=True)
			scr = self.parse_script(create_a[6])

			tempdis = create_a[8]
			if tempdis != '-1':
				if tempdis == '0':
					scr = 'tempdisable 1800 {0}'.format(scr)
				else:
					scr = 'tempdisable {0} {1}'.format(tempdis,scr)

			ampcen = create_a[9]
			autoguide = 'OFF'
			if create_a[10] == '1':
				autoguide = 'ON'

			if len(create_a) > 16 and float(create_a[16]) != 0:
				scr = 'ampcen={0} A 0.001 {1} autoguide={2} {3}'.format(ampcen,self.acqexp,autoguide,scr)
			else:
				scr = 'ampcen={0} autoguide={1} {2}'.format(ampcen,autoguide,scr)

			if len(create_a) > 15 and float(create_a[15]) != 0:
				scr = 'FOC.FOC_TOFF+={0} {1}'.format(float(create_a[15]),scr)

			if int(create_a[7]) > 1:
				scr = 'for ' + create_a[7] + ' { ' + scr + ' }'

			self.cl_append(_('setting script to {0}').format(scr),intend=True)
			if doit:
				login.getProxy().loadJson('/api/change_script',{'id':create_tar_id,'c':'KCAM','s':scr})
			# airmass limit
			airm = float(create_a[13])
			if airm > 0:
				self.cl_append(_('setting airmass limit to {0}').format(airm),intend=True)
				if doit:
					login.getProxy().loadJson('/api/change_constraints',{'id':create_tar_id,'cn':'airmass','ci':':{0}'.format(airm)})
			# lunar distance
			lun = float(create_a[14])
			if lun > 0 and lun != 90:
				if lun > 90:
					self.cl_append(_('setting constraint to not observe target while moon is above local horizon'),intend=True)
					if doit:
						login.getProxy().loadJson('/api/change_constraints',{'id':create_tar_id,'cn':'lunarAltitude','ci':':0'})
				else:
					self.cl_append(_('setting constraint to minimal lunar distance to {0} degrees').format(lun),intend=True)
					if doit:
						login.getProxy().loadJson('/api/change_constraints',{'id':create_tar_id,'cn':'lunarDistance','ci':'{0}:'.format(lun)})

			# PI string 
			if self.pi is not None:
				self.cl_append(_('setting PI to {0}').format(self.pi),intend=True)
				if doit:
					login.getProxy().loadJson('/api/tlabs_set',{'id':create_tar_id,'ltype':rts2const.LABEL_PI,'ltext':self.pi})

			# PROGRAM string
			if self.program is not None:
				self.cl_append(_('setting PROGRAM to {0}').format(self.program),intend=True)
				if doit:
					login.getProxy().loadJson('/api/tlabs_set',{'id':create_tar_id,'ltype':rts2const.LABEL_PROGRAM,'ltext':self.program})
			if doit:
				self.created_targets_id.append(create_tar_id)
			
			# enable/disable target 
			ce = 0
			if create_enabled:
				self.cl_append(_('enabling target for autonomouse selection'),intend=True)
				ce = 1
			else:
				self.cl_append(_('disabling target for autonomouse selection'),intend=True)
			if doit:
				login.getProxy().loadJson('/api/update_target',{'id':create_tar_id,'enabled':ce})

		gobject.idle_add(self.set_page_complete,page,True)

	def addTarget(self,tarid,tarname,tarra,tardec,a):
		if tarid:
			self.targetstore.data.append([True,False,False,a[0],a[1],a[2],tarid,tarname,tarra,tardec,a[6],a])
		else:
			self.targetstore.data.append([True,True,False,a[0],a[1],a[2],-1,'',-float('inf'),-float('inf'),a[6],a])

	def prepare(self,assistant,page):
		if page == self.page0:
			self.targetstore.data.clear()

			self.set_page_complete(self.page_match,False)

		elif page == self.page_match:

			if len(self.targetstore.data) == 0:
				f = open(self.page0.get_filename(),'r')
				self.lines = f.readlines()
				self.pm_tt = len(self.lines)

				gobject.idle_add(self.process_line)

		elif page == self.page_create_summary:
			self.create_summary = gtk.TextBuffer()
			self.create_summary_text.set_buffer(self.create_summary)

			self.set_page_complete(self.page_create_summary,False)
			self.active_text = self.create_summary_text

			login.getProxy().queue(self.create_target, _('Generating summary page preview'), self.page_create_summary, False)

		elif page == self.page_create:
			self.create_log = gtk.TextBuffer()
			self.create_text.set_buffer(self.create_log)

			self.set_page_complete(self.page_create, False)
			self.active_text = self.create_text

			login.getProxy().queue(self.create_target, _('Creating targets'), self.page_create)

	def selection_activated(self,filechooser):
		if filechooser.get_filename():
			self.set_page_complete(self.page0,True)
		else:
			self.set_page_complete(self.page0,False)

if __name__ == '__main__':
  	l = login.Login()
	l.signon()

	t = ImportAssistant()
	t.connect('close',gtk.main_quit)
	t.show()

	gtk.main()
