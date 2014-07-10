#
# Widget with values selected for ploting. Enables selection of
# color for plot, scale, ..
#
# Petr Kubanek <petr@kubanek.net>

import gtk
from .records import Records

class Value:
	def __init__(self):
		self.device = ''
		self.variable = ''

class ValueEditDialog(gtk.Dialog):
	def __init__(self):
		gtk.Dialog.__init__(self, 'Value edit', None,
		  gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		  (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
		   gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

		hbox = gtk.HBox()

		self.records = Records()
		recframe = gtk.Frame('Variable')
		recframe.add(self.records)
		hbox.pack_start(recframe, True)

		scalebox = gtk.VBox()
		self.linear = gtk.RadioButton(None, 'Linear')
		scalebox.pack_start(self.linear, False)
		scalebox.pack_start(gtk.RadioButton(self.linear, 'Log'), False)
		scalebox.pack_end(gtk.Label(), True)

		scaleframe = gtk.Frame('Scale')
		scaleframe.add(scalebox)

		hbox.pack_end(scaleframe, False)

		self.vbox.pack_start(hbox, True)
		hbox.show_all()

	def getScale(self):
		if (self.linear.get_active()):
			return 'linear'
		return 'log'

class Values(gtk.VBox):
	def __init__(self):
		gtk.VBox.__init__(self)
		self.store = gtk.ListStore(str,str,str,int)
		self.treeview = gtk.TreeView(self.store)
		self.treeview.append_column(gtk.TreeViewColumn('Device', gtk.CellRendererText(), text=0))
		self.treeview.append_column(gtk.TreeViewColumn('Value', gtk.CellRendererText(), text=1))
		self.treeview.append_column(gtk.TreeViewColumn('Scale', gtk.CellRendererText(), text=2))

		self.pack_start(self.treeview, True)
		button = gtk.Button(label='Add new')
		button.connect('clicked', self.add_new)
		self.pack_start(button, False)

		button = gtk.Button(label='Delete selected')
		button.connect('clicked', self.del_selected)
		self.pack_start(button, False)
	
	def add_new(self, widget):
		dialog = ValueEditDialog()
		dialog.run()
		sel = dialog.records.getSelected()
		self.store.append([sel[1], sel[2], dialog.getScale(), sel[0]])
		dialog.destroy()

	def del_selected(self,widget):
		self.store.remove(self.treeview.get_selection().get_selected()[1])

	"""Return array of arrays, containing name, id, and scale of variables."""
	def getVariables(self):
		iter = self.store.get_iter_first()
		ret = []
		while (iter != None):
			ret.append(self.store.get(iter, 1, 3, 2))
			iter = self.store.iter_next(iter)
		return ret
