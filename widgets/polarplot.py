# coding=utf-8
import gtk
import math
import cairo

class PolarPlot(gtk.DrawingArea):
	def __init__(self):
		gtk.DrawingArea.__init__(self)
		self.set_size_request(100, 100)

		self.connect('expose-event', self.expose)

		self.__telaltaz = {}

	def expose(self, widget, event):
		area = widget.get_allocation()
		self.draw(widget.window.cairo_create(), area)

	def set_telaltaz(self, alt, az, label):
		if alt is not None and az is not None:
			self.__telaltaz[label] = [alt, az, label]
		else:
			self.__telaltaz[label] = None
		self.queue_draw()

	def cross(self, context, x, y, label=None):
		context.move_to(x - 5, y)
		context.line_to(x + 5, y)

		context.move_to(x, y - 5)
		context.line_to(x, y + 5)

		context.stroke()

		if label is not None:
			context.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
			context.set_font_size(12)
			x_bearing, y_bearing, width, height = context.text_extents(label)[:4]
			context.move_to(x - width / 2 - x_bearing, y - 12 - height / 2 - y_bearing)
			context.show_text(label)		

	def draw(self, context, area):
		size = min(area.width, area.height) - 18

		radius = size / 2.0

		c_x = area.width / 2.0
		c_y = area.height / 2.0

		context.set_source_rgba(1, 0, 0, 1.0)

		context.set_line_width(2.0)
		context.arc(c_x, c_y, radius, 0, 2*math.pi)
		context.stroke()

		context.set_source_rgba(0, 1, 0, 1.0)
		context.set_line_width(2.0)
		context.arc(c_x, c_y, 2*radius/3, 0, 2*math.pi)
		context.stroke()
		
		context.set_line_width(1.0)
		
		context.set_source_rgba(1,0,0,1.0)
		context.move_to(c_x - radius, c_y)
		context.line_to(c_x + radius, c_y)
		context.move_to(c_x, c_y - radius)
		context.line_to(c_x, c_y + radius)
		context.stroke()

		context.set_source_rgba(1, 0, 0, 1.0)
		context.move_to(c_x - radius-10, c_y)
		context.show_text('E')
		context.move_to(c_x + radius+1, c_y)
		context.show_text('W')
		context.move_to(c_x , c_y- radius-8)
		context.show_text('N')
		context.move_to(c_x , c_y+ radius+14)
		context.show_text('S')
		context.set_source_rgba(0, 1, 0, 1.0)
		context.move_to(c_x , c_y+ 2*radius/3+8)
		context.show_text('Alt = 30°')


		for k in self.__telaltaz.keys():
			if self.__telaltaz[k] is not None:
				r = (90 - self.__telaltaz[k][0]) / 90.0 * radius

				an = math.radians(self.__telaltaz[k][1])

				self.cross(context, c_x + r * math.sin(an), c_y + r * math.cos(an), self.__telaltaz[k][2])
