#!/usr/bin/python
# Python widget that simulates an LCD dot-matrix display
# like those found on stereo equipment. Based on gslimp3
#
# Copyright (C) 2005 Gerome Fournier <jefke(at)free.fr>
# Copyright (C) 2008 John Stowers <john.stowers@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import gtk
import gtk.glade
import sys
import signal
import struct
import socket
import random

_KEY_MAPPING = {
	"0": '0',
	"1": '1',
	"2": '2',
	"3": '3',
	"4": '4',
	"5": '5',
	"6": '6',
	"7": '7',
	"8": '8',
	"9": '9',
	"KP_0": '0',
	"KP_1": '1',
	"KP_2": '2',
	"KP_3": '3',
	"KP_4": '4',
	"KP_5": '5',
	"KP_6": '6',
	"KP_7": '7',
	"KP_8": '8',
	"KP_9": '9',
	"UP": 'UP',
	"RIGHT": 'RIGHT',
	"LEFT": 'LEFT',
	"DOWN": 'DOWN',
	"PAGE_UP": 'VOLUP',
	"PAGE_DOWN": 'VOLDOWN',
	"HOME": 'NOW_PLAYING',
	"RETURN": 'PLAY',
	"KP_ENTER": 'PLAY',
	"SPACE": 'PAUSE',
	"BRACKETLEFT": 'REW',
	"BRACKETRIGHT": 'FWD',
	"PLUS": 'ADD',
	"KP_ADD": 'ADD',
	"SLASH": 'SEARCH',
	"KP_DIVIDE": 'SEARCH',
	"A": 'SLEEP',
	"B": 'BRIGHTNESS',
	"F": 'SIZE',
	"R": 'REPEAT',
	"S": 'SHUFFLE',
}

class LCDWidget:
	"GTK+ LCD Widget"

	def __init__(self, widget, rows, cols):
		"Instantiate a LCD widget"
		self.rows = rows
		self.cols = cols
		self._area = widget
		self._pix = None
		self._table = {}
		self._area.connect("configure-event", self._configure_cb)
		self._area.connect("expose-event", self._expose_cb)

	def set_zoom_factor(self, factor):
		"Set the zoom factor"
		self._factor = factor
		self._border = 5
		self._cborder = 3*factor
		self._cwidth = 9*factor
		self._cheight = 13*factor
		self._width = 2*self._border + \
				(self._cwidth+self._cborder)*self.cols + self._cborder
		self._height = 2*self._border + \
				(self._cheight+self._cborder)*self.rows + self._cborder
		self._area.set_size_request(self._width, self._height)
		
	def get_zoom_factor(self):
		return self._factor

	def refresh(self):
		"Refresh the LCD widget"
		self._area.queue_draw_area(0, 0, self._width, self._height)

	def draw_char(self, row, col, charindex):
		"""Draw the character stored at position 'charindex' in the internal
		   character definition table, on the LCD widget
		"""
		if not self._pix:
			return
		x = col * (self._cwidth+self._cborder) + self._border + self._cborder
		y = row * (self._cheight+self._cborder) + self._border + self._cborder
		self._pix.draw_drawable(self._back, self._table[charindex], \
				0, 0, x, y, self._cwidth, self._cheight)

	def set_brightness_percentage(self, percentage):
		fg_colors = {
			100: "#00ff96",
			75: "#00d980",
			50: "#00b269",
			25: "#008c53",
			0: "#303030"
		}
		if percentage not in fg_colors.keys():
			return
		if hasattr(self, "_brightness_percentage") \
			and self._brightness_percentage == percentage:
			return
		self._brightness_percentage = percentage
		self._set_colors(["#000000", "#303030", fg_colors[percentage]])
		self._load_font_definition()
		
	def get_brightness_percentage(self):
		return self._brightness_percentage

	def clear(self):
		"Clear the LCD display"
		for row in range(self.rows):
			for col in range(self.cols):
				self.draw_char(row, col, 32)
		self.refresh()

	def set_button_press_event_cb(self, cb):
		"Setup a callback when a mouse button is pressed on the LCD display"
		self._area.add_events(gtk.gdk.BUTTON_PRESS_MASK)
		self._area.connect("button_press_event", cb)

	def set_scroll_event_cb(self, cb):
		"Setup a callback when wheel mouse is used on the LCD display"
		self._area.connect("scroll_event", cb)

	def create_char(self, charindex, shape):
		"""Insert a new char in the character table definition,
		   at position 'charindex', based on 'shape'
		"""
		pix = gtk.gdk.Pixmap(self._area.window, self._cwidth, self._cheight)
		pix.draw_rectangle(self._back, True, 0, 0, self._cwidth, self._cheight)
		for x in range(5):
			for y in range(7):
				pix.draw_rectangle(self._charbg, True, \
					x*2*self._factor, y*2*self._factor, \
					self._factor, self._factor)
		for index in range(35):
			if shape[index] == "1":
				row = index / 5
				col = index - row*5
				pix.draw_rectangle(self._charfg, True, \
					col*2*self._factor, row*2*self._factor, \
					self._factor, self._factor)
		self._table[charindex] = pix

	def print_line(self, string):
		"Print a single line on the LCD display"
		self.clear()
		for i in range(len(string[:self.cols])):
			self.draw_char(0, i, ord(string[i]))
		self.refresh()

	def _configure_cb(self, widget, event):
		x, y, width, height = widget.get_allocation()
		self._pix = gtk.gdk.Pixmap(widget.window, width, height)
		self.set_brightness_percentage(100)
		self._pix.draw_rectangle(self._back, True, 0, 0, width, height)
		self._load_font_definition()
		self.clear()
		return True

	def _expose_cb(self, widget, event):
		if self._pix:
			widget.window.draw_drawable(self._back, self._pix, 0, 0, 0, 0, \
					self._width, self._height)
		return False

	def _set_colors(self, colors):
		for widget, color in zip(["_back", "_charbg", "_charfg"], colors):
			exec "self.%s = gtk.gdk.GC(self._pix)" % widget
			exec "self.%s.set_rgb_fg_color(gtk.gdk.color_parse('%s'))" \
				% (widget, color)

	def _load_font_definition(self):
		self.create_char(0x00,'00000000000000000000000000000000000')
		self.create_char(0x01,'00000000000000000000000000000000000')
		self.create_char(0x02,'00000000000000000000000000000000000')
		self.create_char(0x03,'00000000000000000000000000000000000')
		self.create_char(0x04,'00000000000000000000000000000000000')
		self.create_char(0x05,'00000000000000000000000000000000000')
		self.create_char(0x06,'00000000000000000000000000000000000')
		self.create_char(0x07,'00000000000000000000000000000000000')
		self.create_char(0x08,'00000000000000000000000000000000000')
		self.create_char(0x09,'00000000000000000000000000000000000')
		self.create_char(0x0a,'00000000000000000000000000000000000')
		self.create_char(0x0b,'00000000000000000000000000000000000')
		self.create_char(0x0c,'00000000000000000000000000000000000')
		self.create_char(0x0d,'00000000000000000000000000000000000')
		self.create_char(0x0e,'00000000000000000000000000000000000')
		self.create_char(0x0f,'00000000000000000000000000000000000')
		self.create_char(0x10,'10000100001000010000100001000010000')
		self.create_char(0x11,'11000110001100011000110001100011000')
		self.create_char(0x12,'11100111001110011100111001110011100')
		self.create_char(0x13,'11110111101111011110111101111011110')
		self.create_char(0x14,'11111111111111111111111111111111111')
		self.create_char(0x15,'01111011110111101111011110111101111')
		self.create_char(0x16,'00111001110011100111001110011100111')
		self.create_char(0x17,'00011000110001100011000110001100011')
		self.create_char(0x18,'00001000010000100001000010000100001')
		self.create_char(0x19,'00100001100010100101011011110001100')
		self.create_char(0x1a,'11000110000000000111010000100000111')
		self.create_char(0x1b,'11000110000000001111010000111001000')
		self.create_char(0x1c,'00000000001111101110001000000000000')
		self.create_char(0x1d,'00000010000110001110011000100000000')
		self.create_char(0x1e,'00000000100011001110001100001000000')
		self.create_char(0x1f,'00000000000010001110111110000000000')
		self.create_char(0x20,'00000000000000000000000000000000000')
		self.create_char(0x21,'00100001000010000100000000000000100')
		self.create_char(0x22,'01010010100101000000000000000000000')
		self.create_char(0x23,'01010010101111101010111110101001010')
		self.create_char(0x24,'00100011111010001110001011111000100')
		self.create_char(0x25,'11000110010001000100010001001100011')
		self.create_char(0x26,'01100100101010001000101011001001101')
		self.create_char(0x27,'01100001000100000000000000000000000')
		self.create_char(0x28,'00010001000100001000010000010000010')
		self.create_char(0x29,'10000010000010000100001000100010000')
		self.create_char(0x2a,'00000001001010101110101010010000000')
		self.create_char(0x2b,'00000001000010011111001000010000000')
		self.create_char(0x2c,'00000000000000000000011000010001000')
		self.create_char(0x2d,'00000000000000011111000000000000000')
		self.create_char(0x2e,'00000000000000000000000001100011000')
		self.create_char(0x2f,'00000000010001000100010001000000000')
		self.create_char(0x30,'01110100011001110101110011000101110')
		self.create_char(0x31,'00100011000010000100001000010001110')
		self.create_char(0x32,'01110100010000100010001000100011111')
		self.create_char(0x33,'11111000100010000010000011000101110')
		self.create_char(0x34,'00010001100101010010111110001000010')
		self.create_char(0x35,'11111100001111000001000011000101110')
		self.create_char(0x36,'00110010001000011110100011000101110')
		self.create_char(0x37,'11111000010001000100010000100001000')
		self.create_char(0x38,'01110100011000101110100011000101110')
		self.create_char(0x39,'01110100011000101111000010001001100')
		self.create_char(0x3a,'00000011000110000000011000110000000')
		self.create_char(0x3b,'00000011000110000000011000010001000')
		self.create_char(0x3c,'00010001000100010000010000010000010')
		self.create_char(0x3d,'00000000001111100000111110000000000')
		self.create_char(0x3e,'10000010000010000010001000100010000')
		self.create_char(0x3f,'01110100010000100010001000000000100')
		self.create_char(0x40,'01110100010000101101101011010101110')
		self.create_char(0x41,'01110100011000110001111111000110001')
		self.create_char(0x42,'11110100011000111110100011000111110')
		self.create_char(0x43,'01110100011000010000100001000101110')
		self.create_char(0x44,'11100100101000110001100011001011100')
		self.create_char(0x45,'11111100001000011110100001000011111')
		self.create_char(0x46,'11111100001000011110100001000010000')
		self.create_char(0x47,'01110100011000010111100011000101111')
		self.create_char(0x48,'10001100011000111111100011000110001')
		self.create_char(0x49,'01110001000010000100001000010001110')
		self.create_char(0x4a,'00111000100001000010000101001001100')
		self.create_char(0x4b,'10001100101010011000101001001010001')
		self.create_char(0x4c,'10000100001000010000100001000011111')
		self.create_char(0x4d,'10001110111010110101100011000110001')
		self.create_char(0x4e,'10001100011100110101100111000110001')
		self.create_char(0x4f,'01110100011000110001100011000101110')
		self.create_char(0x50,'11110100011000111110100001000010000')
		self.create_char(0x51,'01110100011000110001101011001001101')
		self.create_char(0x52,'11110100011000111110101001001010001')
		self.create_char(0x53,'01111100001000001110000010000111110')
		self.create_char(0x54,'11111001000010000100001000010000100')
		self.create_char(0x55,'10001100011000110001100011000101110')
		self.create_char(0x56,'10001100011000110001100010101000100')
		self.create_char(0x57,'10001100011000110101101011010101010')
		self.create_char(0x58,'10001100010101000100010101000110001')
		self.create_char(0x59,'10001100011000101010001000010000100')
		self.create_char(0x5a,'11111000010001000100010001000011111')
		self.create_char(0x5b,'01110010000100001000010000100001110')
		self.create_char(0x5c,'10001010101111100100111110010000100')
		self.create_char(0x5d,'01110000100001000010000100001001110')
		self.create_char(0x5e,'00100010101000100000000000000000000')
		self.create_char(0x5f,'00000000000000000000000000000011111')
		self.create_char(0x60,'01000001000001000000000000000000000')
		self.create_char(0x61,'00000000000111000001011111000101111')
		self.create_char(0x62,'10000100001000010110110011000111110')
		self.create_char(0x63,'00000000000111010000100001000101110')
		self.create_char(0x64,'00001000010000101101100111000101111')
		self.create_char(0x65,'00000000000111010001111111000001110')
		self.create_char(0x66,'00110010010100011100010000100001000')
		self.create_char(0x67,'00000011111000110001011110000101110')
		self.create_char(0x68,'10000100001011011001100011000110001')
		self.create_char(0x69,'00000001000000001100001000010001110')
		self.create_char(0x6a,'00010000000011000010000101001001100')
		self.create_char(0x6b,'01000010000100101010011000101001001')
		self.create_char(0x6c,'01100001000010000100001000010001110')
		self.create_char(0x6d,'00000000001101010101101011000110001')
		self.create_char(0x6e,'00000000001011011001100011000110001')
		self.create_char(0x6f,'00000000000111010001100011000101110')
		self.create_char(0x70,'00000000001111010001111101000010000')
		self.create_char(0x71,'00000000000110110011011110000100001')
		self.create_char(0x72,'00000000001011011001100001000010000')
		self.create_char(0x73,'00000000000111010000011100000111110')
		self.create_char(0x74,'01000010001110001000010000100100110')
		self.create_char(0x75,'00000000001000110001100011001101101')
		self.create_char(0x76,'00000000001000110001100010101000100')
		self.create_char(0x77,'00000000001000110001100011010101010')
		self.create_char(0x78,'00000000001000101010001000101010001')
		self.create_char(0x79,'00000000001000110001011110000101110')
		self.create_char(0x7a,'00000000001111100010001000100011111')
		self.create_char(0x7b,'00010001000010010000001000010000010')
		self.create_char(0x7c,'00100001000010000100001000010000100')
		self.create_char(0x7d,'01000001000010000010001000010001000')
		self.create_char(0x7e,'00000001000001011111000100010000000')
		self.create_char(0x7f,'00000001000100011111010000010000000')
		self.create_char(0x80,'01010000000010001010100011111110001')
		self.create_char(0x81,'00100000000010001010100011111110001')
		self.create_char(0x82,'00100010100010001010100011111110001')
		self.create_char(0x83,'00010001000111000001011111000101111')
		self.create_char(0x84,'00100000000111000001011111000101111')
		self.create_char(0x85,'11111110001100011111110001100011111')
		self.create_char(0x86,'10001011101000110001100011000101110')
		self.create_char(0x87,'00000010100000001110100011000101110')
		self.create_char(0x88,'00001011101001110101110010111010000')
		self.create_char(0x89,'00000000100111010101101010111001000')
		self.create_char(0x8a,'10001000001000110001100011000101110')
		self.create_char(0x8b,'00000010100000010001100011001101101')
		self.create_char(0x8c,'00000100000100000100000100000100000')
		self.create_char(0x8d,'00001000101111100100111110100010000')
		self.create_char(0x8e,'00000010001010110101000100000000000')
		self.create_char(0x8f,'01111100000111010001011100000111110')
		self.create_char(0x90,'01110101001010011111101001010010111')
		self.create_char(0x91,'00000000001101000101111111010001011')
		self.create_char(0x92,'00110010010100011110010000100011111')
		self.create_char(0x93,'11100100101110010010101111001010011')
		self.create_char(0x94,'00000011101111111111111110111000000')
		self.create_char(0x95,'00000011101000110001100010111000000')
		self.create_char(0x96,'00000001000111011111011100010000000')
		self.create_char(0x97,'00000001000101010001010100010000000')
		self.create_char(0x98,'00100001000010000000001000010000100')
		self.create_char(0x99,'01111100001000010000011110010001000')
		self.create_char(0x9a,'00000000010001100101010011000111111')
		self.create_char(0x9b,'00010001000100000100000100000011111')
		self.create_char(0x9c,'01000001000001000100010000000011111')
		self.create_char(0x9d,'00001000010010101001111110100000100')
		self.create_char(0x9e,'00100011101010100100001000010000100')
		self.create_char(0x9f,'00100001000010000100101010111000100')
		self.create_char(0xa0,'00000000000000000000000000000000000')
		self.create_char(0xa1,'00000000000000000000111001010011100')
		self.create_char(0xa2,'00111001000010000100000000000000000')
		self.create_char(0xa3,'00000000000000000100001000010011100')
		self.create_char(0xa4,'00000000000000000000100000100000100')
		self.create_char(0xa5,'00000000000000001100011000000000000')
		self.create_char(0xa6,'00000111110000111111000010001000100')
		self.create_char(0xa7,'00000000001111100001001100010001000')
		self.create_char(0xa8,'00000000000001000100011001010000100')
		self.create_char(0xa9,'00000000000010011111100010000100110')
		self.create_char(0xaa,'00000000000000011111001000010011111')
		self.create_char(0xab,'00000000000001011111001100101010010')
		self.create_char(0xac,'00000000000100011111010010101001000')
		self.create_char(0xad,'00000000000000001110000100001011111')
		self.create_char(0xae,'00000000001111000010111100001011110')
		self.create_char(0xaf,'00000000000000010101101010000100110')
		self.create_char(0xb0,'00000000000000011111000000000000000')
		self.create_char(0xb1,'11111000010010100110001000010001000')
		self.create_char(0xb2,'00001000100010001100101000010000100')
		self.create_char(0xb3,'00100111111000110001000010001000100')
		self.create_char(0xb4,'00000111110010000100001000010011111')
		self.create_char(0xb5,'00010111110001000110010101001000010')
		self.create_char(0xb6,'01000111110100101001010010100110010')
		self.create_char(0xb7,'00100111110010011111001000010000100')
		self.create_char(0xb8,'00000011110100110001000010001001100')
		self.create_char(0xb9,'01000011111001000010000100001000100')
		self.create_char(0xba,'00000111110000100001000010000111111')
		self.create_char(0xbb,'01010111110101001010000100010001000')
		self.create_char(0xbc,'00000110000000111001000010001011100')
		self.create_char(0xbd,'00000111110000100010001000101010001')
		self.create_char(0xbe,'01000111110100101010010000100000111')
		self.create_char(0xbf,'00000100011000101001000010001001100')
		self.create_char(0xc0,'00000011110100110101000110001011000')
		self.create_char(0xc1,'00010111000010011111001000010001000')
		self.create_char(0xc2,'00000101011010110101000010001000100')
		self.create_char(0xc3,'01110000001111100100001000010001000')
		self.create_char(0xc4,'01000010000100001100010100100001000')
		self.create_char(0xc5,'00100001001111100100001000100010000')
		self.create_char(0xc6,'00000011100000000000000000000011111')
		self.create_char(0xc7,'00000111110000101010001000101010000')
		self.create_char(0xc8,'00100111110001000100011101010100100')
		self.create_char(0xc9,'00010000100001000010000100010001000')
		self.create_char(0xca,'00000001000001010001100011000110001')
		self.create_char(0xcb,'10000100001111110000100001000001111')
		self.create_char(0xcc,'00000111110000100001000010001001100')
		self.create_char(0xcd,'00000010001010000010000010000100000')
		self.create_char(0xce,'00100111110010000100101011010100100')
		self.create_char(0xcf,'00000111110000100001010100010000010')
		self.create_char(0xd0,'00000011100000001110000000111000000')
		self.create_char(0xd1,'00000001000100010000100011111100001')
		self.create_char(0xd2,'00000000010000101010001000101010000')
		self.create_char(0xd3,'00000111110100011111010000100000111')
		self.create_char(0xd4,'01000010001111101001010100100001000')
		self.create_char(0xd5,'00000011100001000010000100001011111')
		self.create_char(0xd6,'00000111110000111111000010000111111')
		self.create_char(0xd7,'01110000001111100001000010001000100')
		self.create_char(0xd8,'10010100101001010010000100010001000')
		self.create_char(0xd9,'00000001001010010100101011010110110')
		self.create_char(0xda,'00000100001000010001100101010011000')
		self.create_char(0xdb,'00000111111000110001100011000111111')
		self.create_char(0xdc,'00000111111000110001000010001000100')
		self.create_char(0xdd,'00000110000000000001000010001011100')
		self.create_char(0xde,'00100100100100000000000000000000000')
		self.create_char(0xdf,'11100101001110000000000000000000000')
		self.create_char(0xe0,'00000000000100110101100101001001101')
		self.create_char(0xe1,'01010000000111000001011111000101111')
		self.create_char(0xe2,'00000011101000111110100011111010000')
		self.create_char(0xe3,'00000000000111010000011001000101110')
		self.create_char(0xe4,'00000100011000110011111011000010000')
		self.create_char(0xe5,'00000000000111110100100101000101110')
		self.create_char(0xe6,'00000001100100110001111101000010000')
		self.create_char(0xe7,'00000000000111110001011110000101110')
		self.create_char(0xe8,'00000000000011100100001001010001000')
		self.create_char(0xe9,'00010110100001000000000000000000000')
		self.create_char(0xea,'00000000100000000010000101001001100')
		self.create_char(0xeb,'10100010001010000000000000000000000')
		self.create_char(0xec,'00000001000111010100101010111000100')
		self.create_char(0xed,'01000010001110001000111000100001111')
		self.create_char(0xee,'01110000001011011001100011000110001')
		self.create_char(0xef,'00000010100000001110100011000101110')
		self.create_char(0xf0,'00000101101100110001111101000010000')
		self.create_char(0xf1,'00000011011001110001011110000100001')
		self.create_char(0xf2,'00000011101000111111100011000101110')
		self.create_char(0xf3,'00000000000000001011101011101000000')
		self.create_char(0xf4,'00000000000111010001100010101011011')
		self.create_char(0xf5,'01010000001000110001100011001101101')
		self.create_char(0xf6,'11111100000100000100010001000011111')
		self.create_char(0xf7,'00000000001111101010010100101010011')
		self.create_char(0xf8,'11111000001000101010001000101010001')
		self.create_char(0xf9,'00000000001000110001011110000101110')
		self.create_char(0xfa,'00000000011111000100111110010000100')
		self.create_char(0xfb,'00000000001111101000011110100110001')
		self.create_char(0xfc,'00000000001111110101111111000110001')
		self.create_char(0xfd,'00000001000000011111000000010000000')
		self.create_char(0xfe,'00000000000000000000000000000000000')
		self.create_char(0xff,'11111111111111111111111111111111111')

class Slimp3LCD(LCDWidget):
	"An LCD display abble to parse Slimp3 LCD display packets"
	_CODE_DELAY = 0
	_CODE_CMD = 2
	_CODE_DATA = 3

	_CMD_CLEAR = 0
	_CMD_HOME = 1
	_CMD_MODE = 2
	_CMD_DISPLAY = 3
	_CMD_SHIFT = 4
	_CMD_FUNC_SET = 5
	_CMD_CG_ADDR = 6
	_CMD_DD_ADDR = 7
	
	def parse_lcd_packet(self, lcd_packet):
		"Parse a SLIMP3 LCD packet"
		self.addr = 0
		self.shift = 1
		i = 0
		while i < len(lcd_packet)/2:
			chunk = socket.ntohs(struct.unpack("H", lcd_packet[i*2:i*2+2])[0])
			code = (chunk & 0xFF00) >> 8
			cmd = chunk & 0x00FF
			if code == self._CODE_DELAY:
				pass
			elif code == self._CODE_CMD:
				i += self._handle_command(cmd, lcd_packet[i*2:])
			elif code == self._CODE_DATA:
				row = self.addr / self.cols
				col = self.addr - self.cols*row
				self.draw_char(row, col, cmd)
				self._move_cursor(self.shift)
			i += 1
		self.refresh()

	def _handle_command(self, cmd, string):
		"Handle LCD commands"
		if cmd >> self._CMD_CLEAR == 1:
			self.clear()
			self.addr = 0
			self.shift = 1
		elif cmd >> self._CMD_HOME == 1:
			self.addr = 0
		elif cmd >> self._CMD_MODE == 1:
			if cmd & 2 != 0:
				self.shift = 1
			else:
				self.shift = -1
		elif cmd >> self._CMD_DISPLAY == 1:
			pass
		elif cmd >> self._CMD_SHIFT == 1:
			if cmd & 0x04:
				self.move_cursor(-1)
			else:
				self.move_cursor(1)
		elif cmd >> self._CMD_FUNC_SET == 1:
			return self._handle_function_set(cmd, string[2:4])
		elif cmd >> self._CMD_CG_ADDR == 1:
			return self._handle_char_definition(cmd, string[2:16])
		elif cmd >> self._CMD_DD_ADDR == 1:
			pass
		return 0

	def _handle_function_set(self, cmd, string):
		"Handle Brightness stuff"
		if ord(string[0]) == 3:
			self.set_brightness_percentage(100 - 25 * ord(string[1]))
			return 1
		else:
			return 0
		
	def _handle_char_definition(self, char, string):
		"Create a char as defined by 'string'"
		if len(string) != 14:
			print >>sys.stderr, "Character definition has a wrong size!"
			return 0
		shape = [' '] * 35
		index = (0x3f & char) >> 3;
		for i in range(7):
			line = ord(string[2*i + 1])
			for j in range(5):
				if 1 & (line >> (4 - j)):
					shape[i*5+j] = "1"
		self.create_char(index, shape)
		# defining a new char consume 7 extra command codes
		return 7

	def _move_cursor(self, shift):
		self.addr += shift
		if self.addr < 0:
			self.addr = 0
		elif self.addr > self.rows * self.cols - 1:
			self.addr = self.rows * self.cols - 1


class Slimp3Gui:
	"Main GUI"

	def __init__(self):
		"Instantiate the application"
		self._setup_widgets()
		self._set_zoom_factor(1)

	def run(self):
		"Start the application"
		try:
			signal.signal(signal.SIGINT, self._quit)
			signal.signal(signal.SIGTERM, self._quit)
			self._window.show_all()
			self.print_bollocks()
			gtk.main()
		except KeyboardInterrupt:
			self._quit()
		except:
			raise

	def _quit(self, *args):
		gtk.main_quit()

	def _setup_widgets(self):
		self._window = gtk.Window()
		self._window.hide()
		self._window.connect("destroy", self._quit)
		widget = gtk.DrawingArea()
		self._window.add(widget)
		self.lcd_display = Slimp3LCD(widget, 2, 40)
		self.lcd_display.set_button_press_event_cb(self.button_press_cb)
		self.lcd_display.set_scroll_event_cb(self.scroll_event_cb)
		
	def button_press_cb(self, widget, event):
		self.print_bollocks(start=random.randint(16,30))
		return True

	def scroll_event_cb(self, widget, event):
		change = 0
		
		if (event.state & gtk.gdk.CONTROL_MASK) == gtk.gdk.CONTROL_MASK:
			if event.direction == gtk.gdk.SCROLL_UP:
				change = 25
			elif event.direction == gtk.gdk.SCROLL_DOWN:
				change = -25

			p = self.lcd_display.get_brightness_percentage()
			self._set_brightness_percentage(p+change)
				

		else:
			if event.direction == gtk.gdk.SCROLL_UP:
				change = 1
			elif event.direction == gtk.gdk.SCROLL_DOWN:
				change = -1
			
			z = self.lcd_display.get_zoom_factor()
			self._set_zoom_factor(z+change)

		self.print_bollocks()
		return True

	def _set_zoom_factor(self, factor):
		if factor < 1:
			factor = 1
		if factor > 2:
			factor = 2
		self.lcd_display.set_zoom_factor(factor)
		
	def _set_brightness_percentage(self, percent):
		if percent < 0:
			percent = 0
		if percent > 100:
			percent = 100
		self.lcd_display.set_brightness_percentage(percent)
		
	def print_bollocks(self, start=16):
		self.lcd_display.clear()
		self.lcd_display.print_line("ABCDEFGHIJKLMNOPabcdefghij")
		for i in range(0,40):
			self.lcd_display.draw_char(1,i,start+i)
		self.lcd_display.refresh()
		
if __name__ == "__main__":
	if len(sys.argv) > 1:
		print >>sys.stderr, "Usage: %s\nSlimp3 client written in python." \
				% sys.argv[0]
		sys.exit(1)
	app = Slimp3Gui()
	app.run()
