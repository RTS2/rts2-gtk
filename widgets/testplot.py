#!/usr/bin/python
#
# Script demonstrating real-time plots using JSON and GTK (TimePlot) interface.
# Copyright (C) 2012 Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import timeplot
import time
import random
import gobject
import gtk
import sys
import os
import signal
import threading
import math
import rts2.rtsapi

from optparse import OptionParser

parser = OptionParser()
parser.add_option('--server', help='URL to RTS2 XML-RPC server', action='store', dest='server', default='http://localhost:8889')
parser.add_option('--user', help='RTS2 web server username', action='store', dest='user', default=None)
parser.add_option('--password', help='password for web user', action='store', dest='password', default=None)
parser.add_option('--verbose', help='print in/out communication', action='store_true', dest='verbose', default=False)

parser.add_option('--measurements', help='maximal number of measurements to show', type='int', dest='num_mes', default=60)

(options, args) = parser.parse_args()

if len(args) == 0:
	print >>sys.stderr, 'You must specify at least one variable to monitor'
	sys.exit(1)

j = rts2.rtsapi.JSONProxy(options.server, options.user, options.password, verbose = options.verbose)

gobject.threads_init()

w = gtk.Window()

def push_value(plot,device,value,num_mes):
	r = j.getResponse('/api/push', args=[(device, value)])
	while True:
		res = j.chunkJson(r)
		n = time.time()
		plot.points = plot.points[-num_mes:]
		plot.points.append([n, res['v'][value]])
		plot.x_ruler.lower = plot.points[0][0]
		plot.x_ruler.upper = n + 1
		plot.auto_y_range()
		gobject.idle_add(plot.queue_draw)

t_size = int(math.ceil(math.sqrt(len(args))))

mt = gtk.Table(t_size, t_size)

n = time.time()

x = 0
y = 0

for a in args:
	dot = a.find('.')
	if dot < 0:
		print >>sys.stderr, 'you must provide value-device pairs separated with .'
  	device = a[:dot]
	value = a[dot + 1:]
	p = timeplot.TimePlot(60, timeplot.PLOT_FILL)
	p.x_ruler.lower = n
	th = threading.Thread(target = push_value, args = (p, device, value, options.num_mes, ))
	th.setDaemon(True)
	th.start()
	mt.attach(p, x, x + 1, y, y + 1, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL)

	x += 1
	if x >= t_size:
		x = 0
		y += 1

w.add(mt)
w.connect('destroy', gtk.main_quit)
w.show_all()

gtk.main()
