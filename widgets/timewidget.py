# Time widget - HH:MM:SS widget
#
# Petr Kubanek <petr@kubanek.net>

import gtk

class DigitsDisplay(gtk.SpinButton):
	def __init__(self, adjustment=None, width=2):
		if adjustment is None:
			adjustment = gtk.Adjustment(0, 0, 60, 1, 5)
		gtk.SpinButton.__init__(self, adjustment)
		self.set_numeric(True)
		self.set_width_chars(width)

		self.connect('output', self.show_leading_zeros)
	
	def show_leading_zeros(self, spin_button):
		adjustment = spin_button.get_adjustment()
		spin_button.set_text(('{0:0' + str(self.get_width_chars()) + 'd}').format(int(adjustment.get_value())))
		return True

class TimeWidget(gtk.HBox):
	def __init__(self, label=None):
		gtk.HBox.__init__(self)

		self.hh = DigitsDisplay(gtk.Adjustment(0, 0, 24, 1, 2))
		self.mm = DigitsDisplay()
		self.ss = DigitsDisplay()

		if label is not None:
			self.pack_start(gtk.Label(label), True, True)

		self.pack_start(self.hh, False, False)
		self.pack_start(gtk.Label(':'), False, False)
		self.pack_start(self.mm, False, False)
		self.pack_start(gtk.Label(':'), False, False)
		self.pack_start(self.ss, False, False)

	def set_time(self, hh, mm, ss):
		self.hh.set_value(hh)
		self.mm.set_value(mm)
		self.ss.set_value(ss)

	def get_time(self):
		try:
			return self.get_hours() * 3600 + self.get_minutes() * 60 + self.get_seconds()
		except Exception, ex:
			import traceback
			traceback.print_exc()
			return None

	def set_seconds(self, seconds):
		if seconds is None:
			self.set_time('--', '--', '--')
		else:
			ss = int(seconds % 60)
			mm = (seconds - ss) / 60
			hh = int(mm / 60)
			mm = int(mm % 60)
			self.set_time(hh, mm, ss)
	
	def get_hours(self):
		return self.hh.get_value_as_int()
	
	def get_minutes(self):
		return self.mm.get_value_as_int()
	
	def get_seconds(self):
		return self.ss.get_value_as_int()
