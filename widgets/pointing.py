#
# Pointing widget - for small telescope movements
#
# Petr Kubanek <petr@kubanek.net>

import gtk

import login
import radec

class Pointing(gtk.Table):

	move_scale = 1/60.0
	scale_mul = 1
	dist = 0

	k_left = [gtk.keysyms.Left,gtk.keysyms.KP_4]
	k_right = [gtk.keysyms.Right,gtk.keysyms.KP_6]
	k_up = [gtk.keysyms.Up,gtk.keysyms.KP_8]
	k_down = [gtk.keysyms.Down,gtk.keysyms.KP_2]
	k_stop = [gtk.keysyms.Home,gtk.keysyms.KP_5,gtk.keysyms.KP_Begin]
	k_div = [gtk.keysyms.KP_Divide]
	k_mul = [gtk.keysyms.KP_Multiply]

	k_1 = [gtk.keysyms.KP_1]
	k_3 = [gtk.keysyms.KP_3]
	k_7 = [gtk.keysyms.KP_7]
	k_9 = [gtk.keysyms.KP_9]

	support_set_and_go = True

	def __init__(self,telescope_name = None, support_set_and_go = True, show_multipliers = True):
		gtk.Table.__init__(self,3,5)
		if telescope_name is None:
			try:
				self.telescope_name = login.getProxy().loadJson('/api/devbytype',{"t":2})[0]
			except IndexError:
				msgbox = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=_("Cannot find any telescope attached to the system."))
				msgbox.run()
				msgbox.hide()
				exit(0)
		else:
			self.telescope_name = telescope_name

		self.support_set_and_go = support_set_and_go

		self.b_ra_minus = gtk.ToggleButton()
		self.b_ra_minus.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_BACK,gtk.ICON_SIZE_DIALOG))
		self.b_ra_plus = gtk.ToggleButton()
		self.b_ra_plus.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_FORWARD,gtk.ICON_SIZE_DIALOG))
		self.b_dec_plus = gtk.ToggleButton()
		self.b_dec_plus.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_UP,gtk.ICON_SIZE_DIALOG))
		self.b_dec_minus = gtk.ToggleButton()
		self.b_dec_minus.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN,gtk.ICON_SIZE_DIALOG))

		self.b_stop = gtk.ToggleButton()
		self.b_stop.set_image(gtk.image_new_from_stock(gtk.STOCK_STOP,gtk.ICON_SIZE_DIALOG))
		
		self.b_ra_minus.connect('pressed', self.button_pressed)
		self.b_ra_plus.connect('pressed', self.button_pressed)
		self.b_dec_minus.connect('pressed', self.button_pressed)
		self.b_dec_plus.connect('pressed', self.button_pressed)

		self.b_ra_minus.connect('released', self.button_released)
		self.b_ra_plus.connect('released', self.button_released)
		self.b_dec_minus.connect('released', self.button_released)
		self.b_dec_plus.connect('released', self.button_released)

		self.b_stop.connect ('pressed', self.stop_pressed)

		self.ra_swap = gtk.ToggleButton(label='RA')
		self.dec_swap = gtk.ToggleButton(label='DEC')

		self.attach(self.b_ra_minus,0,1,2,3)
		self.attach(self.b_ra_plus,2,3,2,3)
		self.attach(self.b_dec_plus,1,2,1,2)
		self.attach(self.b_dec_minus,1,2,3,4)

		self.attach(self.b_stop,1,2,2,3)

		self.attach(self.ra_swap,0,1,4,5)
		self.attach(self.dec_swap,2,3,4,5)

		self.connect('key-press-event', self.key_press)
		self.connect('key-release-event', self.key_release)

		self.b_stop.grab_focus()

		if show_multipliers:
			self.b_div = gtk.ToggleButton(label='/')
			self.b_mul = gtk.ToggleButton(label='*')

			self.b_div.connect('pressed', self.button_pressed)
			self.b_mul.connect('pressed', self.button_pressed)

			self.b_div.connect('released', self.button_released)
			self.b_mul.connect('released', self.button_released)

			self.attach(self.b_div,1,2,0,1)
			self.attach(self.b_mul,2,3,0,1)

			self.b_dist = [gtk.ToggleButton(label='1x'),gtk.ToggleButton(label='2x'),gtk.ToggleButton(label='4x'),gtk.ToggleButton(label='8x')]

			for b in self.b_dist:
				b.connect('pressed', self.dist_pressed)
		  		b.connect('released', self.dist_pressed)

			self.attach(self.b_dist[0],0,1,3,4)
			self.attach(self.b_dist[1],2,3,3,4)
			self.attach(self.b_dist[2],0,1,1,2)
			self.attach(self.b_dist[3],2,3,1,2)

			self.set_dist(0)
		else:
			self.b_div = None
			self.b_mul = None
			self.b_dist = None

		try:
			login.getProxy().setValue(self.telescope_name,'ra_guide', '0')
			self.ra_swap.connect('clicked', self.stop_pressed)
			login.getProxy().setValue(self.telescope_name,'dec_guide', '0')
			self.dec_swap.connect('clicked', self.stop_pressed)
		except Exception, fault:
			self.support_set_and_go = False


	"""Retuns scale used for movements. Returned number is in degrees."""	
	def get_move_scale(self):
		return self.scale_mul * float(self.move_scale) / 3600.0

	"""Set scale used for movements."""
	def set_move_scale(self,move_scale):
		self.move_scale = move_scale

	"""Returns plus and minus directions - swap them if buttons are swapped"""
	def get_dir_minus(self,swap):
		if(swap):
			return '2'
		else:
			return '1'
	
	def get_dir_plus(self,swap):
		if(swap):
			return '1'
		else:
			return '2'

	def button_pressed(self,widget):
		ra_off = 0
		dec_off = 0
		self.b_stop.grab_focus()
#		offsets for telescopes which support go and leave command
		if (self.support_set_and_go):
			if (widget == self.b_ra_minus):
				login.getProxy().setValue(self.telescope_name,'ra_guide', self.get_dir_minus(self.ra_swap.get_active()))
			elif (widget == self.b_ra_plus):
				login.getProxy().setValue(self.telescope_name,'ra_guide', self.get_dir_plus(self.ra_swap.get_active()))
			elif (widget == self.b_dec_minus):
				login.getProxy().setValue(self.telescope_name,'dec_guide', self.get_dir_minus(self.dec_swap.get_active()))
			elif (widget == self.b_dec_plus):
				login.getProxy().setValue(self.telescope_name,'dec_guide', self.get_dir_plus(self.dec_swap.get_active()))
			elif (widget == self.b_stop):
				login.getProxy().setValue(self.telescope_name,'dec_guide', '0')
				login.getProxy().setValue(self.telescope_name,'ra_guide', '0')
				self.b_ra_minus.set_active(False)
				self.b_ra_plus.set_active(False)
				self.b_dec_minus.set_active(False)
				self.b_dec_plus.set_active(False)
			else:
				return False
		else:
			if widget == self.b_ra_minus:
				ra_off = -1
			elif widget == self.b_ra_plus:
				ra_off = +1
			elif widget == self.b_dec_minus:
				dec_off = -1
			elif widget == self.b_dec_plus:
				dec_off = +1
			elif widget == self.b_mul:
				if self.scale_mul < 16.0:
					self.scale_mul *= 2
			elif widget == self.b_div:
				if self.scale_mul > 1:
					self.scale_mul /= 2
			else:
			  	return False

			if widget == self.b_mul or widget == self.b_div:
				self.set_dist()

			if self.ra_swap.get_active():
				ra_off *= -1
			if self.dec_swap.get_active():
			  	dec_off *= -1

			login.getProxy().incValue(self.telescope_name,'OFFS', '%f %f' % (ra_off * self.get_move_scale(), dec_off * self.get_move_scale()))
		widget.set_active(True)
		self.b_stop.set_active(False)
		return True

	def stop_pressed(self,widget):
		if self.support_set_and_go == True:
			login.getProxy().setValue(self.telescope_name,'ra_guide', '0')
			login.getProxy().setValue(self.telescope_name,'dec_guide', '0')
		login.getProxy().executeCommand(self.telescope_name,'stop')
		self.b_ra_minus.set_active(False)
		self.b_ra_plus.set_active(False)
		self.b_dec_minus.set_active(False)
		self.b_dec_plus.set_active(False)
		self.b_stop.set_active(True)
		return True
	
	def button_released(self,widget):
		widget.set_active(False)
		return True

	def set_dist(self,num = None):
		if num is not None:
			self.dist = num
		n = 0
		dist = [60.0, 300.0, 1200.0, 3600.0]
		for b in self.b_dist:
			b.set_active(n == self.dist)
			b.set_label(radec.dist_string(self.scale_mul * dist[n]))
			n += 1

		return self.set_move_scale(dist[self.dist])

	def dist_pressed(self,widget):
		n = 0
		for x in self.b_dist:
			if widget == x:
				self.set_dist(n)
				break
			n += 1
		return True

	def key_press(self,widget,key):
		but = None
		if key.keyval in self.k_div and self.b_div is not None:
			but = self.b_div
		elif key.keyval in self.k_mul and self.b_mul is not None:
			but = self.b_mul
		elif key.keyval in self.k_left:
		  	but = self.b_ra_minus
		elif key.keyval in self.k_right:
			but = self.b_ra_plus
		elif key.keyval in self.k_up:
			but = self.b_dec_plus
		elif key.keyval in self.k_down:
			but = self.b_dec_minus
		elif key.keyval in self.k_stop:
			self.stop_pressed(widget)
			return True
		elif key.keyval in self.k_1 and self.b_dist is not None:
			self.set_dist(0)
			return True
		elif key.keyval in self.k_3 and self.b_dist is not None:
			self.set_dist(1)
			return True
		elif key.keyval in self.k_7 and self.b_dist is not None:
			self.set_dist(2)
			return True
		elif key.keyval in self.k_9 and self.b_dist is not None:
			self.set_dist(3)
			return True
		else:
		  	return False
		# if possible, null action which is in progress..
		if (self.support_set_and_go == True):
			if key.keyval in self.k_left and self.b_ra_plus.get_active()==True:
				self.b_ra_plus.set_active(False)
				login.getProxy().setValue(self.telescope_name,'ra_guide', '0')
				return True
			if key.keyval in self.k_right and self.b_ra_minus.get_active()==True:
				self.b_ra_minus.set_active(False)
				login.getProxy().setValue(self.telescope_name,'ra_guide', '0')
				return True
			if key.keyval in self.k_down and self.b_dec_plus.get_active()==True:
				self.b_dec_plus.set_active(False)
				login.getProxy().setValue(self.telescope_name,'dec_guide', '0')
				return True
			if key.keyval in self.k_up and self.b_dec_minus.get_active()==True:
				self.b_dec_minus.set_active(False)
				login.getProxy().setValue(self.telescope_name,'dec_guide', '0')
				return True
		self.button_pressed(but)
		return True

	"""This should be called from top window on key relase as well"""	
	def key_release(self,widget,key):
		but = None
		if key.keyval in self.k_left:
		  	but = self.b_ra_minus
		elif key.keyval in self.k_right:
			but = self.b_ra_plus
		elif key.keyval in self.k_up:
			but = self.b_dec_plus
		elif key.keyval in self.k_down:
			but = self.b_dec_minus
		elif key.keyval in self.k_div and self.b_div is not None:
			but = self.b_div
		elif key.keyval in self.k_mul and self.b_mul is not None:
			but = self.b_mul
		else:
		  	return False
		if (self.support_set_and_go == False):
			self.button_released(but)
		return True
