#!/usr/bin/python
#
# Script to import schedules from SSON. Create target in RTS2 database, and
# queues schedules to it.
#
# (C) 2011 Petr Kubanek, Institute of Physics <kubanek@fzu.cz>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place - Suite 330, Boston, MA  02111-1307, USA.

import ftplib
import datetime
import sys
import string
import re
import radec
import login
import rts2const

class Exposure:
	def __init__(self):
		self.filter = None
		self.duration = None

class Block:
	def __init__(self,duration,observer):
		self.source = None
		self.ra = self.dec = None
		self.exposures = []
		self.blockrep = 1
		self.duration = duration
		self.observer = observer
		
		self.vh = {}

		self.tar_id = None

	def parse(self,key,value):
		self.vh[key] = value

	def generate(self):
		try:
			self.source = self.vh['SOURCE']
			self.ra = radec.from_hms(self.vh['RA'])*15.0
			self.dec = radec.from_hms(self.vh['DEC'])
			fi = string.split(self.vh['FILTER'],',')
			du = string.split(self.vh['DURATION'],',')
			if not (len(fi) == len(du)):
				raise Exception('Length of filters does not match durations')
			for i in range(0,len(fi)):
				eb = Exposure()
				eb.filter = fi[i]
				eb.duration = float(du[i])
				self.exposures.append(eb)
		except Exception,ex:
			print ex
			raise ex

	def create(self):
		# see if there is candidate to macth..
		print 'Trying to find source {0} on {1} {2}'.format(self.source,radec.ra_string(self.ra),radec.dec_string(self.dec))
		candidates = login.getProxy().loadJson('/api/tbyname',{'n':self.source,'pm':0})['d']
		if len(candidates) == 1:
			print 'Matched target {0} to ID {1} by name'.format(self.source,candidates[0][0])
		else:
			candidates = login.getProxy().loadJson('/api/tbydistance',{'ra':self.ra,'dec':self.dec,'radius':0.1})['d']
			if len(candidates) == 1:
				print 'Matched target {0} to {1} with ID {2} by coordinates'.format(self.source,candidates[0][1],candidates[0][0])
			else:
				candidates = None

		if candidates is None or len(candidates) > 1:
			d = login.getProxy().loadJson('/api/create_target',{'tn':self.source,'ra':self.ra,'dec':self.dec})
			self.tar_id = int(d['id'])
			print 'Create target with ID {0}'.format(self.tar_id)
		else:
			self.tar_id = candidates[0][0]

		# now the observer..
		login.getProxy().loadJson('/api/tlabs_delete',{'id':self.tar_id,'ltype':rts2const.LABEL_PI})
		login.getProxy().loadJson('/api/tlabs_add',{'id':self.tar_id,'ltype':rts2const.LABEL_PI,'ltext':self.observer})
		# script
		s = self.script()
		print 'Setting script to',s
		login.getProxy().loadJson('/api/change_script',{'id':self.tar_id,'c':'C0','s':s})

	
	def script(self):
		ret = ''
		for e in self.exposures:
			if len(ret):
				ret += ' '
			ret += 'filter={0} E {1}'.format(e.filter,e.duration)
		return ret

class Schedule:
	def __init__(self):
		self.title = None
		self.observer = None
		self.blocks = []
		self.data = None

	def process_data(self):
		r = re.compile("^\s*(\S*)\s*=\s*('[^']*'|[^']\S*)")
		for x in string.split(self.data,'\n'):
			if re.match(x,'^\s*$') or x[0] == '!':
				continue
			line = r.match(x)
			if line is None:
				print 'unknow line',x
				continue
			key = line.group(1).upper()
			value = line.group(2)
			if value[0] == "'" and value[-1] == "'":
				value = value[1:-1]

			if key == 'TITLE':
				self.title = value
			elif key == 'OBSERVER':
			  	self.observer = value
			elif key == 'BLOCK':
				self.blocks.append(Block(value,self.observer))
			elif len(self.blocks) > 0:
				self.blocks[-1].parse(key,value)
			else:
				print 'unknow key',key

		for b in self.blocks:
			b.generate()
			b.create()

	def read_sch(self,data):
		if self.data:
			self.data += '\n'
		else:
			self.data = ''
		self.data += data

if __name__ == "__main__":
	l = login.Login()
	l.signon()
	
	ftp = ftplib.FTP('sierrastars.exavault.com','watcher','ssonwatcher')
	d = datetime.date.today()
	#dn = 'schFiles/' + d.strftime('%d-%B-%y')
	dn = 'schFiles/30-June-11'
	try:
		ftp.cwd(dn)
	except ftplib.error_perm,e:
		print >>sys.stderr, 'Cannot change to directory to {0}:{1}, exiting'.format(dn,e)
		sys.exit(1)
	files = ftp.nlst()
	for sch in files:
		if sch == '.' or sch == '..':
			continue
		print 'Reading',sch
		s = Schedule()
		ftp.retrlines('RETR ' + sch,s.read_sch)
		print 'Processing data'
		s.process_data()
	ftp.quit()
