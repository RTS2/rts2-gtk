""" Simple widget for records selection. 
"""

import gtk

from rts2xmlserver import rts2XmlServer

class Records(gtk.TreeView):
	def __init__(self):
		self.store = gtk.ListStore(str,str,int)
		gtk.TreeView.__init__(self, self.store)
		self.append_column(gtk.TreeViewColumn("Device", gtk.CellRendererText(), text=0))
		self.append_column(gtk.TreeViewColumn("Value", gtk.CellRendererText(), text=1))
		self.buildValueList()

		self.get_selection().set_mode(gtk.SELECTION_SINGLE)

	def buildValueList(self):
		result = rts2XmlServer().rts2.records.values()
		for n in result:
			self.store.append([n['device'],n['value_name'],n['id']])

		self.selected = result[0]

	"""Return selected values."""
	def getSelected(self):
		return self.store.get(self.get_selection().get_selected()[1], 2, 0, 1)
