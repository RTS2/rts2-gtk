#!/usr/bin/env python
"""Load and display targets."""
#
# Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import gtk
import gobject
import gettext
import json
import jsontable
import login
import radec
import script

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class NewTargetDialog(gtk.Assistant):
	"""Dialog to create new target"""
	def __init__(self):
		gtk.Assistant.__init__(self)
		self.set_title(_('Add new target'))
		self.set_geometry_hints(min_width=600,min_height=500)

		self.used_target_id = None

		self.connect('apply',self.apply_pressed)
		self.connect('cancel',self.cancel_pressed)
		self.connect('prepare',self.prepare)

		self.page0 = gtk.VBox(spacing=5)
		hb = gtk.HBox(spacing=5)

		self.append_page(self.page0)
		self.set_page_title(self.page0,_('Entering target name'))
		self.set_page_type(self.page0,gtk.ASSISTANT_PAGE_CONTENT)

		hb.pack_start(gtk.Label(_('Enter new target name')),False,False)
		self.tarname = gtk.Entry()
		hb.pack_end(self.tarname,True)
		self.tarname.connect('changed',self.tarname_changed,self.page0)

		self.page0.pack_start(hb,False,False)

		l = gtk.Label(_('You can specify new target with:'))
		l.set_alignment(0,0.5)
		self.page0.pack_start(l,False,False)

		hb = gtk.HBox(spacing=0)
		hb.pack_start(gtk.Label(),False,False,25)
		hb.pack_start(gtk.LinkButton('http://simbad.u-strasbg.fr','Simbad'),False,False)
		l = gtk.Label(_('database'))
		l.set_alignment(0,0.5)
		hb.pack_end(l,True)

		self.page0.pack_start(hb,False,False)

		self.page1 = gtk.VBox(spacing=5)
		self.append_page(self.page1)

		self.error_label = gtk.Label()
		self.error_label.set_line_wrap(True)

		self.page1.pack_start(self.error_label)
		self.set_page_title(self.page1, _('Resolving target'))
		self.set_page_type(self.page1,gtk.ASSISTANT_PAGE_CONTENT)
		self.set_page_complete(self.page1,False)

		self.page2 = gtk.VBox(spacing=5)

		l = gtk.Label(_('Create new target'))
		l.set_alignment(0,0.5)
		self.page2.pack_start(l,False,False)

		self.resolved_selected = gtk.RadioButton()
		self.resolved_not_selected = gtk.RadioButton(self.resolved_selected)
		self.resolved_not_selected.set_active(True)
		self.resolved_selected.connect('toggled',self.resolved_toggled)
		self.resolved_name = gtk.Entry()
		self.resolved_name.set_text('')
		self.resolved_name.connect('changed',self.tarname_changed,self.page1)
		self.resolved_ra = gtk.Label('123456789012')
		self.resolved_dec = gtk.Label('123456789012')

		self.resolved_desc = gtk.Label()
		self.resolved_desc.set_alignment(0,0.5)

		hb = gtk.HBox(spacing=5)
		hb.pack_start(self.resolved_selected,False,False)
		hb.pack_start(self.resolved_name,True)

		hb.pack_end(self.resolved_dec,False,False)
		hb.pack_end(self.resolved_ra,False,False)

		self.page2.pack_start(hb,False,False)

		l = gtk.Label(_('or please select one from following existing targets'))
		l.set_alignment(0,0.5)
		self.page2.pack_start(l,False,False)

		self.old_path = None
		self.nearest = jsontable.JsonTable('/api/tbystring',data=json.loads('{"h":[{"n":"Target ID","t":"n","prefix":"/targets/","href":0,"c":0},{"n":"Target Name","t":"a","prefix":"/targets/","href":0,"c":1},{"n":"RA","t":"r","c":2},{"n":"DEC","t":"d","c":3},{"n":"Description","t":"s","c":4},{"n":"Distance","t":"d","c":5}],"d":[]}'),radio_select=_('Sel'),radio_select_func=self.toggled_target)

		self.page2.pack_end(self.nearest,True)

		self.append_page(self.page2)
		self.set_page_type(self.page2,gtk.ASSISTANT_PAGE_CONTENT)
		self.set_page_title(self.page2,_('Select target'))

		self.page3 = gtk.VBox(spacing=5)

		self.append_page(self.page3)
		self.set_page_type(self.page3,gtk.ASSISTANT_PAGE_PROGRESS)
		self.set_page_title(self.page3,_('Creating new target'))

		self.page4 = script.ScriptEditor()

		self.append_page(self.page4)

		self.set_page_type(self.page4,gtk.ASSISTANT_PAGE_CONTENT)
		self.set_page_title(self.page4,_('Edit target script'))

		self.page_progress = gtk.VBox(spacing=5)
		self.index_progress = self.append_page(self.page_progress)
		self.set_page_type(self.page_progress, gtk.ASSISTANT_PAGE_PROGRESS)
		self.set_page_title(self.page_progress, _("Retrieving data"))

		self.page_progress_pb = gtk.ProgressBar()
		self.page_progress.pack_start(self.page_progress_pb, True, False)

		self.set_forward_page_func(self.forward,None)

		self.show_all()
	
	def tarname_changed(self,entry,page):
		if len(entry.get_text()) > 0:
			self.set_page_complete(page,True)
		else:
			self.set_page_complete(page,False)

	def toggled_target(self,cell,path):
		p = self.nearest.sm.convert_path_to_child_path(path)
		if self.old_path is not None and not (self.old_path == p):
			self.nearest.data.set(self.nearest.data.get_iter(self.old_path),len(self.nearest.data.names),False)
		if self.old_path is None or not (self.old_path == p):
			self.nearest.data.set(self.nearest.data.get_iter(p),len(self.nearest.data.names),True)
		self.old_path = p
		self.resolved_not_selected.set_active(True)
		self.set_page_complete(self.page2,True)
	
	def resolved_toggled(self,button):
		if button.get_active() == True and self.old_path is not None:
			self.nearest.data[self.old_path][len(self.nearest.data.names)] = False
			self.old_path = None
		self.set_page_complete(self.page2,True)

	def apply_pressed(self,assistant):
		if self.get_current_page() == 1:
			gtk.main_quit()
	
	def cancel_pressed(self,assistant):
		gtk.main_quit()
	
	def prepare(self,assistant,page):
		if page == self.page1:
			if len(self.resolved_name.get_text()):
				self.set_current_page(0)
				self.resolved_name.set_text('')
				return

			def __fill_target(self):
				try:
					self.tars = login.getProxy().loadJson('/api/tbystring',{'ts':self.tarname.get_text(),'nearest':20})
				except Exception,ex:
					self.set_page_title(self.page1,_('Cannot resolve target'))
					self.error_label.set_text(_('Cannot resolve name of target {0} from Simbad.').format(self.tarname.get_text(), ex))
					self.set_page_complete(self.page1,True)
					return
				self.resolved_name.set_text(self.tars['name'])
				self.resolved_ra.set_text(radec.ra_string(self.tars['ra']))
				self.resolved_dec.set_text(radec.dec_string(self.tars['dec']))
				self.resolved_desc.set_text(self.tars['desc'])
				self.nearest.reload('/api/tbystring',data=self.tars['nearest']['d'])
				self.nearest.append('/api/tbyname',{'n':self.tarname.get_text(),'ra':self.tars['ra'],'dec':self.tars['dec']})
				gobject.idle_add(self.set_current_page, 2)

			self.set_current_page(self.index_progress)
			login.getProxy().queue(__fill_target, _('Resolving target {0}').format(self.tarname.get_text()), self)
		# create new target	
		elif page == self.page3:
			if self.resolved_selected.get_active():
				def __create(self):
					saved = login.getProxy().loadJson('/api/create_target',{'tn':self.resolved_name.get_text(),'ra':self.tars['ra'],'dec':self.tars['dec'],'desc':self.resolved_desc.get_text()})

					l = gtk.Label(_('Created target {0} with coordinates {1} {2} and target ID {3}').format(self.resolved_name.get_text(),radec.ra_string(self.tars['ra']),radec.dec_string(self.tars['dec']),saved['id']))
					l.set_line_wrap(True)
					self.page3.pack_start(l)

					self.set_page_title(self.page3,_('Created new target'))

					self.used_target_id = saved['id']

					self.set_title(_('Editing new target {0} ({1})').format(self.resolved_name.get_text(),self.used_target_id))
					gobject.idle_add(self.set_current_page, 3)

				if self.used_target_id is None:
					self.set_current_page(self.index_progress)
					login.getProxy().queue(__create, self)
					return
			else:
				i = None
				for x in self.nearest.data:
					if x[5]:
						i = x
				l = gtk.Label(_('Using target named {0} with ID {1} on coordinates {2} {3}'.format(i[1],i[0],radec.ra_string(i[2]),radec.dec_string(i[3]))))

				l.set_line_wrap(True)
				self.page3.pack_start(l)

				self.set_page_title(self.page3,_('Using existing target'))

				self.used_target_id = i[0]

				self.set_title(_('Editing target {0} ({1})').format(i[1],self.used_target_id))

			self.page3.show_all()
			self.set_page_complete(self.page3, True)
			self.commit()
		elif page == self.page4:
			self.page4.script.set_target(self.used_target_id, 'C0')
			self.set_page_complete(self.page4, True)

		elif page == self.page_progress:
			def __progress(self):
				self.page_progress_pb.pulse()
				return self.get_current_page() == self.index_progress

			gobject.timeout_add(50, __progress, self)

	def forward(self,current_page,user_data):
		if current_page == 1:
			return 0
		if current_page == 2:
			if self.resolved_selected:
				return 3
			else:
				return 4
		else:
			return current_page + 1

if __name__ == '__main__':
  	l = login.Login()
	l.signon(startQueue=True)

	t = NewTargetDialog()
	t.show()

	gtk.main()
