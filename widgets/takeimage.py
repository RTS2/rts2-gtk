#!/usr/bin/env python
# Test image taking routines
# Copyright (C) 2011,2012 Petr Kubanek <petr@kubanek.net>
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

import login
import time
import gtk
import threading
import traceback
import gettext
import gobject
import struct

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

class CameraWindow(gtk.Window):
	def __init__(self,camera_name,client_only):
		gtk.Window.__init__(self)
		self.camera_name = camera_name
		self.client_only = client_only

		if self.client_only:
			self.set_title(_('Client for camera {0}').format(self.camera_name))
		else:
			self.set_title(_('Images from camera {0}').format(self.camera_name))

		vb = gtk.VBox()

		tt = gtk.Table(2,7)
		tt.set_col_spacings(10)
		tt.set_row_spacings(10)

		def ll(text):
			l = gtk.Label(text)
			l.set_alignment(1,0.5)
			return l

		self.status = gtk.Label('IDLE')
		vb.pack_start(self.status,False,False)

		if not self.client_only:
			tt.attach(ll(_('Exposure time')),0,1,0,1)
			self.exp_t = gtk.SpinButton(gtk.Adjustment(1,0,86400,1,10),digits=2)
			tt.attach(self.exp_t,1,2,0,1)


			tt.attach(ll(_('Binning')),0,1,1,2)

			bins = login.getProxy().getSelection(self.camera_name,'binning')

			self.binnings = []
			hb = gtk.HBox()

			nb = gtk.RadioButton(None,bins[0])
			self.binnings.append(nb)
			hb.pack_start(nb,False,False)
			nb.connect('clicked',self.set_binning)

			for b in bins[1:]:
				nb = gtk.RadioButton(self.binnings[0],b)
				self.binnings.append(nb)
				hb.pack_start(nb,False,False)
				nb.connect('clicked',self.set_binning)
				
			tt.attach(hb,1,2,1,2)

		tt.attach(ll(_('Channel')),0,1,2,3)
		ahb = gtk.HButtonBox()
		self.exp_c = []
		self.sofar = []
		self.tb = []

		try:
			chan = login.getProxy().getValue(self.camera_name,'CHAN')
		except KeyError,ke:
			chan = [True]
		chn = 1
		for x in chan:
			ach = gtk.CheckButton(str(chn))
			ach.set_active(x)
			ahb.add(ach)
			self.exp_c.append(ach)
			self.sofar.append(0)
			self.tb.append(0)
			chn += 1
		tt.attach(ahb,1,2,2,3)

		self.not_orient = [True] * len(chan)

		tt.attach(ll(_('Convert')),0,1,3,4)
		vb2 = gtk.VBox()
		hb = gtk.HBox()

		self.df_keep = gtk.RadioButton(None,'Keep')
		hb.pack_start(self.df_keep,False,False)

		self.df_8b = gtk.RadioButton(self.df_keep,'8bit')
		hb.pack_start(self.df_8b,False,False)

		self.df_16b = gtk.RadioButton(self.df_keep,'16bit')
		hb.pack_start(self.df_16b,False,False)

		vb2.pack_start(hb,False,False)

		hb = gtk.HBox()
		self.smin = gtk.SpinButton(gtk.Adjustment(1,0,0xffff,1,10),digits=0)
		self.smax = gtk.SpinButton(gtk.Adjustment(1,0,0xffff,1,10),digits=0)

		hb.pack_start(self.smin,False,False)
		hb.pack_start(self.smax,False,False)

		vb2.pack_end(hb,False,False)

		tt.attach(vb2,1,2,3,4)

		tt.attach(ll(_('Exposure')),0,1,4,5)
		self.exp_p = gtk.ProgressBar()
		tt.attach(self.exp_p,1,2,4,5)

		tt.attach(ll(_('Readout')),0,1,5,6)
		self.readout_p = gtk.ProgressBar()
		tt.attach(self.readout_p,1,2,5,6)

		tt.attach(ll(_('Data')),0,1,6,7)
		avb = gtk.VBox()
		self.data_pbs = []
		for x in chan:
			apb = gtk.ProgressBar()
			avb.add(apb)
			self.data_pbs.append(apb)
		tt.attach(avb,1,2,6,7)

		vb.pack_start(tt,False,False)

		bb = gtk.HButtonBox()
		if self.client_only:
			self.current_b = gtk.Button(label=_('_Current image'))
			self.current_b.connect('clicked',self.grab_current)
			bb.add(self.current_b)

			self.last_b = gtk.Button(label=_('_Last image'))
			self.last_b.connect('clicked',self.grab_last)
			bb.add(self.last_b)

		else:
			self.exposure_b = gtk.Button(label=_('_Take 1'))
			self.exposure_b.connect('clicked',self.start_exposure)
			bb.add(self.exposure_b)

			self.start_b = gtk.Button(label=_('_Start'))
			self.start_b.connect('clicked',self.start_exposure)
			bb.add(self.start_b)

		self.stop_b = gtk.Button(label=_('_Stop'))
		self.stop_b.connect('clicked',self.stop_exposure)
		self.stop_b.set_sensitive(False)
		bb.add(self.stop_b)

		vb.pack_end(bb,False,False)

		self.add(vb)
		self.show_all()

		self.sta = login.getProxy().loadJson('/api/get',{'d':self.camera_name})

		self.d = None
		self.exp_conn = None

		self.last_lo = 0
		self.last_hi = 1
		self.exptime = None

		try:
			import numpy
			import ds9
			if self.client_only:
				self.d = ds9.ds9(self.camera_name + 'ti-client')
			else:
				self.d = ds9.ds9(self.camera_name + 'ti')
			# map RTS2 data types to numpy types
			self.ds_lock = threading.Lock()

			self.rts2_2_numpy = {8:numpy.uint8,16:numpy.int16,32:numpy.int32,64:numpy.int64,-32:numpy.float,-64:numpy.double,10:numpy.uint8,20:numpy.uint16,40:numpy.uint32}
		except Exception,ex:
			print _("numpy or pyds9 module not present, the program will only take images")

	def set_binning(self,nb):
		login.getProxy().setValue(self.camera_name,'binning',nb.get_label())
		
	def grab_current(self,bb):
		self.stop_b.set_sensitive(True)
		self.current_b.set_sensitive(False)
		self.last_b.set_sensitive(False)
		threading.Thread(target=self.grab_thread,args=('/api/currentimage',)).start()

	def grab_last(self,bb):
		self.stop_b.set_sensitive(True)
		self.current_b.set_sensitive(False)
		self.last_b.set_sensitive(False)
		threading.Thread(target=self.grab_thread,args=('/api/lastimage',)).start()

	def first_channel(self):
		return self.get_active_channels()[0]
	
	def get_active_channels(self):
		chn = 0
		ret = []
		for x in self.exp_c:
			if x.get_active():
				ret.append(chn)
			chn += 1
		return ret

	def prepare_frames(self):
		if self.d:
			self.d.set('tile yes')
			self.d.set('tile mode grid')

	def add_scaling(self,args):
		if not(self.df_keep.get_active()):
			args['smin'] = int(self.smin.get_value())
			args['smax'] = int(self.smax.get_value())
			args['scaling'] = 'linear'
			args['2data'] = 8
		return args

	def grab_thread(self,api):
		if self.exp_conn is None:
			self.exp_conn = login.getProxy().newConnection()

		args = {'ccd':self.camera_name,'chan':self.first_channel()}
		args = self.add_scaling(args)
			
		r = login.getProxy().getResponse(api,args,hlib=self.exp_conn)
		self.prepare_frames()
		self.display_request(r,api,args,self.get_active_channels())
		self.wait_data_end()
		self.current_b.set_sensitive(True)
		self.last_b.set_sensitive(True)

	def start_exposure(self,bb):
		self.exposure_b.set_sensitive(False)
		self.start_b.set_sensitive(False)
		self.stop_b.set_sensitive(True)

		self.tc = 0

		threading.Thread(target=self.exposure_thread,args=(1 if bb == self.exposure_b else None,)).start()
		gobject.timeout_add(500,self.update_status)

	def stop_exposure(self,bb):
		# set togo to 0
		self.numexp = 0
		self.stop_b.set_sensitive(False)
		login.getProxy().executeCommand(self.camera_name,'killall')
		self.tc = 0
	
	def wait_data_end(self):
		togo=range(0,len(self.sofar))
		while self.stop_b.get_sensitive() == True and len(togo) > 0:
			for x in togo:
				if self.sofar[x] == self.tb[x]:
					togo.remove(x)
			time.sleep(0.1)

	def update_pb(self,pb):
		fr = self.sta['sstart']
		to = self.sta['send']
		n = time.time()
		if n < fr:
			pb.set_fraction(0)
			return 0
		elif n > to:
			pb.set_fraction(1)
			return 1

		fra = (n-fr)/(to-fr)
		pb.set_fraction(fra)
		return fra

	def update_status(self):
		if self.tc == 0:
			# check for state only if really needed
			nsta = login.getProxy().loadJson('/api/get',{'d':self.camera_name})
			if not(nsta['state'] == self.sta['state']):
				self.tc = 1
				self.sta = nsta
			self.last_lo = nsta['d']['min']
			self.last_hi = nsta['d']['max']

		if self.sta['state'] & 0x01:
			self.status.set_text(_('Exposing'))
			if self.update_pb(self.exp_p) == 1:
				self.tc = 0
		if self.sta['state'] & 0x02:
			self.status.set_text(_('Reading'))
			self.exp_p.set_fraction(1)
			if self.update_pb(self.readout_p) == 1:
				self.tc = 0
		if self.sta['state'] & 0x03 == 0:
			self.status.set_text(_('IDLE'))
			self.tc = 0
		return not self.exposure_b.get_sensitive()

	def exposure_thread(self,numexp=None):
		if self.exp_conn is None:
			self.exp_conn = login.getProxy().newConnection()
		self.numexp = numexp
		while self.numexp == None or self.numexp > 0:
			self.exp_p.set_fraction(0)
			self.readout_p.set_fraction(0)
			for x in self.data_pbs:
				x.set_fraction(0)

			try:
				self.take_exposure()
			except Exception,ex:
				print 'exposure or readout interrupted',ex
				traceback.print_exc()
				self.exp_conn = None
				self.numexp = 0
			if self.numexp:
				self.numexp -= 1

		self.exposure_b.set_sensitive(True)
		self.wait_data_end()
		self.start_b.set_sensitive(True)
		self.stop_b.set_sensitive(False)

	def take_exposure(self):
		# tady se resi expozice,..
		args = {'ccd':self.camera_name}
		args = self.add_scaling(args)
		if self.exptime is None or not (self.exptime == self.exp_t.get_text()):
			self.exptime = self.exp_t.get_value()
			ret = login.getProxy().loadData('/api/set',{'d':self.camera_name,'n':'exposure','v':self.exptime},hlib=self.exp_conn)
		eargs = args
		eargs['chan'] = self.first_channel()
		r = login.getProxy().getResponse('/api/exposedata',eargs,hlib=self.exp_conn)
		self.prepare_frames()
		self.display_request(r,'/api/currentimage',args,self.get_active_channels())

	def display_request(self,r,api,args,channels=[0]):
		"""Frame - to which frame display data"""
		if not(r.getheader('Content-type') == 'binary/data'):
			raise Exception('wrong header, expecting binary/data, received:',r.getheader('Content-type'),r.read())

		tb = float(r.getheader('Content-length'))

		if self.d:
			import numpy

			frame = channels[0]
			self.sofar[frame] = 44
			self.tb[frame] = tb

			imh = r.read(self.sofar[frame])

			data_type,naxes,w,h,a3,a4,a5,bv,bh,b3,b4,b5,shutter,filt,x,y,chan=struct.unpack('!hhiiiiihhhhhhhhhH',imh)

			# spawn other channels threads
			fr = 1
			for x in channels[1:]:
				args['chan'] = x
				chanr = login.getProxy().getResponse(api,args,hlib=login.getProxy().newConnection())
				threading.Thread(target=self.display_request,args=(chanr,api,args,[fr],)).start()
				fr += 1
			data_pb = self.data_pbs[frame]
			gobject.idle_add(data_pb.set_fraction,0)

			# map data_typ to numpy type
			dt = self.rts2_2_numpy[data_type]

			a = numpy.empty((h,w),dt)
			# fill with square pattern

			if self.last_lo is None:
				self.last_lo = 0
			if self.last_hi is None:
				self.last_hi = 1

			i = 0
			fs = 0
			while i < h:
				step = fs
				j = 0
				while j < w:
					a[i:i+20,j:j+20] = self.last_hi if step else self.last_lo
					step = not step
					j += 20
				i += 20
				fs = not fs

			row = 0

			def __putframe(data,fr):
				try:
					self.ds_lock.acquire()
					self.d.set('frame {0}'.format(fr))
					if self.not_orient[fr]:
						if fr == 1:
							self.d.set('orient x')
						else:
							self.d.set('orient none')
						self.not_orient[fr] = False
					self.d.set_np2arr(data)
					self.d.set('regions','#text({0},{1}) text={{Channel {2}}}'.format(w/2,h/2,fr))
				finally:
					self.ds_lock.release()

			while self.sofar[frame] < tb and self.stop_b.get_sensitive():
			  	line = r.read(a.itemsize * w)
				self.sofar[frame] += a.itemsize * w

				gobject.idle_add(data_pb.set_fraction,self.sofar[frame]/tb)
				a[row] = numpy.fromstring(line,dtype=dt)
				# send to ds9 every 20th row
				if row % 20 == 0:
					__putframe(a,frame)

				row += 1

			if not self.stop_b.get_sensitive():
				r.close()
				self.exp_conn = None

			__putframe(a,frame)

		gobject.idle_add(self.readout_p.set_fraction,1)
		gobject.idle_add(data_pb.set_fraction,1)

if __name__ == '__main__':
	
	l = login.Login()
	l.signon()

	import optparse
	parser = optparse.OptionParser(usage='usage: takeimage.py [--client]')
	parser.add_option('--client',help='act as client',action='store_true',dest='client')
	parser.add_option('--camera',help='take data from this camera',action='store',dest='camera')


	(options,args) = parser.parse_args()
	client = True if options.client else False
	
	w = CameraWindow(options.camera if options.camera else 'C0',client)
	w.connect('destroy',gtk.main_quit)
	gtk.main()
