#
# Dialog box checking for targets and adding them to queue

import gtk
import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class CheckProgress(gtk.Dialog):
	def __init__(self,queue,tl):
		self.queue = queue
		self.msg = gtk.Label()
		self.pb = gtk.ProgressBar()
		self.pb.set_pulse_step(1.0/tl)

		self.vbox.pack_start(self.msg,False,False)
		self.vbox.pack_end(self.pb,False,False)

	def showTarget(self,id,start,end):
		self.msg.set_text(_('Checking target {0}'),
		self.pb.pulse()

