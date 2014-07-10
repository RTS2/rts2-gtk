#
# Pointing widget - for small telescope movements
#
# Petr Kubanek <petr@kubanek.net>

import gtk
import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

import login
from degreelabel import to_limited_hms

class Distances(gtk.Frame):

	distances = [0.02, 1, 1.5]

	k_dist_inc = [gtk.keysyms.plus,gtk.keysyms.KP_Add]
	k_dist_dec = [gtk.keysyms.minus,gtk.keysyms.KP_Subtract]

	def __init__(self,dist_changed):
		gtk.Frame.__init__(self,label=_("Distances"))
		self.dist_changed = dist_changed
		self.vbox = gtk.VBox()
		self.add(self.vbox)
		self.fill_distances()

	def fill_distances(self):
		sg=None
		self.rb=[]
		for s in self.speeds:
			sg=gtk.RadioButton(group=sg,label=to_limited_hms(s,""))
			sg.connect('clicked',self.dist_clicked)
			self.vbox.pack_start(sg)
			self.rb.append(sg)
		self.show_all()
	
	def dist_clicked(self,widget):
		if (widget.get_active()):
			i=self.rb.index(widget)
			login.getProxy().setValue(self.telescope_name,'guiding_speed', str(self.speeds[i]))

	def dist_change(self,speed_ch):
		# find active speed
		active_b = 0
		for b in self.rb:
			if(b.get_active()):
				break
			active_b += 1
		active_b += speed_ch
		if (active_b < 0):
			active_b = 0
		elif (active_b >= len(self.rb)):
			active_b = len(self.rb) - 1
		self.rb[active_b].set_active(True)
	
	def key_press(self,widget,key):
		if key.keyval in self.k_dist_inc:
			return self.dist_change(+1)
		elif key.keyval in self.k_dist_dec:
			return self.dist_change(-1)
		return False
