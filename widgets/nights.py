#!/usr/bin/env python
"""Load and display nights"""
#
# Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import login
import jsontable
import datetime
import gtk
import obsimages

import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class NightDialog(jsontable.JsonSelectDialog):
	def __init__(self):
		self.night = datetime.date.today()

		# look for any old observations within last 12 months
		for c in range(0,11):
		  	d = login.getProxy().loadJson('/nights/{0}/{1}/api'.format(self.night.year,self.night.month))['d']
			if len(d) > 0:
				self.night = self.night.replace(day=d[-1][0])
				break
			
			self.night -= datetime.timedelta(days=28)

		jsontable.JsonSelectDialog.__init__(self,'/nights/{0}/{1}/{2}/api'.format(self.night.year,self.night.month,self.night.day),{},buttons=[(_('Show images'),3),(_('Update'),2),(_('Select night'),1)])
		self.set_title(_('Night {0}').format(self.night))
		self.connect('response',self.responded)

	def responded(self,d,resp):
		if resp == 1:
			self.pickNight()
		elif resp == 2:
			self.reload()
		elif resp == 3:
			 u = obsimages.ImageDialog(self.getSelected(0)[0])

	def pickNight(self):
		cd = gtk.Dialog(title=_('Select night'))
		cal = gtk.Calendar()

		cal.connect('month-changed',self.markMonth)

		cal.select_month(self.night.month - 1,self.night.year)
		cal.select_day(self.night.day)

		cal.set_display_options(gtk.CALENDAR_SHOW_HEADING)
		cal.connect('day-selected',self.changeNight)

		cd.vbox.pack_start(cal)
		cd.show_all()

		cd.connect('destroy',lambda b:self.response(0))

		cd.show()
	
	def markMonth(self,cal):
		"""Marks dates in month where observations were carried"""
		y,m,d = cal.get_date()
		cal.clear_marks()
		mark = login.getProxy().loadJson('/nights/{0}/{1}/api'.format(y,m+1))['d']
		for x in mark:
			if x[1] > 0:
				cal.mark_day(x[0])

	def reload(self):
		self.js.reload('/nights/{0}/{1}/{2}/api'.format(self.night.year,self.night.month,self.night.day))
		self.set_title(_('Night {0}').format(self.night))

	def changeNight(self,cal):
		y,m,d = cal.get_date()
		m += 1
		self.night = self.night.replace(year=y,month=m,day=d)
		self.reload()

if __name__ == '__main__':
  	l = login.Login()
	l.signon()
	
	d = NightDialog()
	d.connect('destroy',gtk.main_quit)
	gtk.main()
