"""Provide cross-API - either KDE or GTK configuration storage"""
import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

try:
	import gconf
except Exception,ex:
	pass

class Config:
	def __init__(self):
		self.gconf = False
		try:
			import gconf
			# connect to gconf - retrieve hosts..
			self.gclient = gconf.client_get_default()
			self.gclient.add_dir("/apps/rts2",gconf.CLIENT_PRELOAD_NONE)
			self.gconf = True
		except Exception,ex:
			pass

	def get_list(self, name):
		if self.gconf:
			return self.gclient.get_list('/apps/rts2/' + name, gconf.VALUE_STRING)
		return []

	def set_list(self, name, list):
		if self.gconf:
		  	return self.gclient.set_list('/apps/rts2/' + name, gconf.VALUE_STRING, list)
		return 0
	
	def get_int(self, name):
		if self.gconf:
		  	return self.gclient.get_int('/apps/rts2/' + name)
		return 0

	def set_int(self, name, value):
		if self.gconf:
		  	return self.gclient.set_int('/apps/rts2/' + name, value)
		return 0

	def get_pair(self, name):
		if self.gconf:
		  	return self.gclient.get_pair('/apps/rts2/' + name, gconf.VALUE_STRING, gconf.VALUE_STRING)
		return (None, None)

	def set_pair(self, name, t1, t2):
		if self.gconf:
		  	return self.gclient.set_pair('/apps/rts2/' + name, gconf.VALUE_STRING, gconf.VALUE_STRING, t1, t2)
		return 
	
	def get_bool(self, name):
		if self.gconf:
			return self.gclient.get_bool('/apps/rts2/' + name, value)
		return False
	
	def set_bool(self, name, value):
		if self.gconf:
			return self.gclient.set_bool('/apps/rts2/' + name, value)
		return False
