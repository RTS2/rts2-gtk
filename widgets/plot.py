#
# Plot time graph in a widget
#
# Petr Kubanek <petr@kubanek.net>

import gtk
import math

from array import array as marray
from matplotlib.dates import date2num
from matplotlib.figure import Figure
from matplotlib.ticker import NullLocator
from numpy import arange, sin, pi
from rts2xmlserver import rts2XmlServer

import matplotlib.dates as mdates
import matplotlib

# uncomment to select /GTK/GTKAgg/GTKCairo
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
#from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvas

class Plot(FigureCanvas):
	def __init__(self,t_from,t_to):
		self.figure = Figure(figsize=(10,2), dpi=80)
		self.t_from = t_from
		self.t_to = t_to
		self.t_diff = math.fabs(t_from - t_to)

		self.axis = None
	
		FigureCanvas.__init__(self,self.figure)
	
	# Set new time bounds.
	# Return false if time wasn't changed, and so graph do not require
	# reploting.
	def setNewTime(self,t_from,t_to):
		if (self.t_from == t_from and self.t_to == t_to):
			return False
		if (self.axis):
			self.figure.clf()
			self.axis.clear()
			self.axis = None
		self.t_from=t_from
		self.t_to=t_to
		# get time differences
		self.t_diff = math.fabs(self.t_from - self.t_to)
		return True

	def setAxisLocators(self, axis):
		# half a day..
		if (self.t_diff <= 43200):
			axis.xaxis.set_major_locator(mdates.HourLocator())
			axis.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
		elif (self.t_diff <= 86400):
			axis.xaxis.set_major_locator(mdates.HourLocator(interval=2))
			axis.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
		elif (self.t_diff <= 86400 * 2):
			axis.xaxis.set_major_locator(mdates.HourLocator(interval=4))
			axis.xaxis.set_minor_locator(mdates.MinuteLocator(interval=30))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
		elif (self.t_diff <= 86400 * 10):
			axis.xaxis.set_major_locator(mdates.DayLocator())
			axis.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
		elif (self.t_diff <= 86400 * 33):
			axis.xaxis.set_major_locator(mdates.DayLocator(interval=2))
			axis.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
		else:
			axis.xaxis.set_minor_locator(mdates.DayLocator(interval=5))
			axis.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
			axis.xaxis.set_major_formatter(mdates.DateFormatter('%m'))

	# Returns new axis instance
	# Either create axis from figure, or creat new yaxis with twinx method
	def getAxis(self):
		if (self.axis != None):
			rax = self.axis.twinx()
			self.setAxisLocators(rax)
			return rax

		self.axis = self.figure.add_subplot(111)

		self.axis.grid(True)

		self.setAxisLocators(self.axis)

		self.next_color = 0

		return self.axis

	# Return next color..
	def getNextColor(self):
		color = "brgym"
		c = color[self.next_color]
		self.next_color += 1
		return c

	# Add varible to plot.
	# Adjust scaling, so if dateaxis is too long, it will use averages
	def addVariable(self, label, varid, scale = 'linear'):
		if (self.t_diff <= 86400 * 5):
		  	return self.addExactVariable(label, varid, scale)
		else:
		  	return self.addAveragevariable(label, varid, scale)

	# Adds average variables
	def addAveragevariable(self, label, varid, scale = 'linear'):
		result = rts2XmlServer().rts2.records.averages(varid, self.t_from, self.t_to)
		if (len(result) == 0):
			return
		
		ta = marray('d')
		sa = marray('d')
		mi = marray('d')
		ma = marray('d')

		for x in result:
			ta.append(date2num(x[0]))
			sa.append(x[1])
			mi.append(x[2])
			ma.append(x[3])

		ax = self.getAxis()
		c = self.getNextColor()
		
		ax.plot_date(ta,sa, '-', color=c)
		ax.set_yscale(scale)

		ax.set_ylabel(label, color=c)
		for tl in ax.get_yticklabels():
		  	tl.set_color(c)

		if (matplotlib.__version__ >= '0.98.4'):
			ax.fill_between(ta,mi,ma,alpha=0.5,facecolor='gray')
		else:
			ax.plot_date(ta,mi,'g-')
			ax.plot_date(ta,ma,'g-')
	
	# Plot exactly all numbers from variable.
	# Please note that this might be time consuming if
	# there are much more points..
	def addExactVariable(self, label, varid, scale = 'linear'):
		result = rts2XmlServer().rts2.records.get(varid, self.t_from, self.t_to)
		if (len(result) == 0):
			print "0 records ", varid, self.t_from, self.t_to
			return

		ta = marray('d')
		sa = marray('d')

		for x in result:
			ta.append(date2num(x[0]))
			sa.append(x[1])

		ax = self.getAxis()

		c = self.getNextColor()

		ax.plot_date(ta,sa, c + '-')
		ax.set_yscale(scale)

		ax.set_ylabel(label, color=c)
		for tl in ax.get_yticklabels():
			tl.set_color(c)

