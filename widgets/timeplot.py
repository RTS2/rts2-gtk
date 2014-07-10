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

from houraxis import HourAxis

PLOT_LINE = 0
PLOT_FILL = 1

class TimePlot(gtk.Table):
	"""Widget with time plot.

	"""

	def __init__(self, time_from, interval, plot_style = PLOT_LINE):
		"""
		Interval is length in seconds.
		"""
		gtk.Table.__init__(self, 2, 2, False)
		self.plot_style = plot_style

		# setup plot
		self.plot = gtk.DrawingArea()
		self.plot.set_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
		self.plot.connect('expose-event', self.expose)
		self.attach(self.plot, 1, 2, 0, 1, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL)

		def motion_notify(ruler,event):
			return ruler.emit('motion-notify-event',event)

		self.y_ruler = gtk.VRuler()
		self.y_ruler.set_metric(gtk.PIXELS)
		self.plot.connect_object('motion-notify-event', motion_notify, self.y_ruler)
		self.attach(self.y_ruler, 0, 1, 0, 1, gtk.FILL, gtk.EXPAND | gtk.SHRINK | gtk.FILL)

		self.x_ruler = HourAxis(time_from, interval)
		self.plot.connect_object('motion-notify-event', motion_notify, self.x_ruler)
		self.attach(self.x_ruler, 1, 2, 1, 2, gtk.EXPAND | gtk.SHRINK | gtk.FILL, gtk.FILL)

		# contains x-y pairs
		self.points = []
	
	def set_y_range(self, lower, upper, position, max_size):
		self.y_ruler.set_range(lower, upper, position, max_size)
	
	def auto_y_range(self):
		if len(self.points):
		  	lower = upper = self.points[0][1]
			for p in self.points:
				lower = min(lower, p[1])
				upper = max(upper, p[1])
			self.set_y_range(upper, lower, self.y_ruler.get_range()[2], upper)

	def expose(self, widget, event):
		"""Don't draw if there is 0 time"""
		if self.x_ruler.upper == self.x_ruler.lower:
			return

		area = widget.get_allocation()
		self.sc_x = area.width / (self.x_ruler.upper - self.x_ruler.lower)
		self.draw(widget.window.cairo_create(), area)

	def get_x_from_hour(self, hour):
		return self.sc_x * (hour - self.x_ruler.lower)
	
	def draw(self, context, area):
		if len(self.points):
			context.set_source_rgba(0, 0, 0, 1.0)
			context.set_line_width(1)

			y_lower, y_upper = self.y_ruler.get_range()[0:2]
			if y_lower == y_upper:
				return

			sc_y = area.height / (y_upper - y_lower)

			context.move_to(0, sc_y * (self.points[0][1] - y_lower))
			for p in self.points:
				context.line_to(self.get_x_from_hour(p[0]), sc_y * (p[1] - y_lower))
			context.line_to(area.width, sc_y * (self.points[-1][1] - y_lower))

			if self.plot_style == PLOT_LINE:
				context.stroke()
			elif self.plot_style == PLOT_FILL:
				context.line_to(area.width, area.height)
				context.line_to(0, area.height)
				context.close_path()
				context.fill()
