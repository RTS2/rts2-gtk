#!/usr/bin/python
#
# Copyright (C) 2012 Petr Kubanek, Institute of Physics <petr@kubanek.net>
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
import math
import time
import timeplot
import rts2.target

class ScheduleBlock:
	def __init__(self, target, times=[]):
		self.target = target
		self.times = times
	
	def draw(self, context, area, tp, y, height):
		"""Draw squares when target is scheduled.
		"""
		context.set_source_rgba(1, 0, 0, 0.50)
		for t in self.times:
			f_x = tp.get_x_from_hour(t[0])
			context.rectangle(f_x, y - (height / 2.0), tp.get_x_from_hour(t[1]) - f_x, height)
		context.fill()

class SchedulePlot(timeplot.TimePlot):
	"""Widget with time, plotting scheduling blocks.
	"""
	def __init__(self, time_from, interval):
		timeplot.TimePlot.__init__(self, time_from, interval, timeplot.PLOT_LINE)
		self.targets = []

	def addTarget(self, tar_id, intervals):
		self.targets.append(ScheduleBlock(rts2.target.get(tar_id), intervals))
	
	def draw(self, context, area):
		y = 5
		for tar in self.targets:
			tar.draw(context, area, self, y, 8)
			y += 10

if __name__ == '__main__':
	import login
	
	l = login.Login()
	l.signon()

	w = gtk.Window()

	t = time.time()

	plot = SchedulePlot(t,36000)

	plot.addTarget(1000,[[t,t+2000],[t+2500,t+3000]])
	plot.addTarget(1001,[[t+2300,t+2500],[t+3000,t+2900]])

	w.add(plot)
	w.show_all()

	w.connect('destroy', gtk.main_quit)
	gtk.main()
