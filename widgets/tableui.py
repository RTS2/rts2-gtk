import gtk
import linecell

w = gtk.Window()
t = gtk.Table(2,2)
t.attach(linecell.LineCell(), 0, 1, 0, 1, gtk.FILL | gtk.EXPAND, gtk.FILL | gtk.EXPAND)
t.attach(gtk.Button('Test'), 1, 2, 0, 1, gtk.SHRINK, gtk.SHRINK)

w.add(t)
w.show_all()

w.connect('destroy', gtk.main_quit)
gtk.main()
