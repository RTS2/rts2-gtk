# Label class to display degrees
#
# Petr Kubanek <petr@kubanek.net>

import gtk
from radec import to_hms

"""Converts string to D M S pair, discarding values which are 0."""
def to_limited_hms(deg,append=''):
	label = ''
	(sign, d, m, s) = to_hms(deg)
	if (d > 0):
		label += "%.0fd" % (d)
	if (m > 0):
	  	label += "%02.0f'" % (m)
	if (s > 0):
	  	label += '%06.3f"' % (s)
	return label

class DegreeLabel(gtk.Label):
	def __init__(self,deg,append = ''):
		# choose how to display degree
		label = ''
		gtk.Label.__init__(to_limited_hms(deg) + append)
