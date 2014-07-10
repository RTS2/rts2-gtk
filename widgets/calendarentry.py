# Simple calendar entry. Picked from the web

import pygtk
import gtk
import datetime
import time
import gobject
import string

class CalendarEntry (gtk.HBox):
        __gsignals__ = {
                'changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, ))
        }
        def __init__ (self,currentDate = datetime.datetime.today()):
                gtk.HBox.__init__ (self, False, 0)
                self.calendar = gtk.Calendar ()
                self.entry = gtk.Entry ()
		self.entry.set_width_chars (10)
		self.time = gtk.Entry ()
		self.time.set_width_chars (5)
                self.button = gtk.Button (label = '...')
                self.cwindow = gtk.Window (gtk.WINDOW_TOPLEVEL)
                self.display = False

                self.cwindow.set_position (gtk.WIN_POS_MOUSE)
                self.cwindow.set_decorated (False)
                self.cwindow.set_modal (True)
                self.cwindow.add (self.calendar)
               
                self.pack_start (self.entry, False, True, 0)
		self.pack_start (self.time, False, True, 0)
                self.pack_start (self.button, True, False, 0)
               
                self.__connect_signals ()
                self.update_entry ()

                self.set_date (currentDate)
                               
        def __connect_signals (self):
                #self.day_selected_handle = self.calendar.connect ('day-selected', self.update_entry)
                self.day_selected_double_handle = self.calendar.connect ('day-selected-double-click', self.hide_widget)
		self.time_changed_handle = self.time.connect ('focus-out-event', self.update_entry)
                self.clicked_handle = self.button.connect ('clicked', self.show_widget)
                self.activate = self.entry.connect ('activate', self.update_calendar)
                self.focus_out = self.entry.connect ('focus-out-event', self.focus_out_event)
               
        def __block_signals (self):
                #self.calendar.handler_block (self.day_selected_handle)
                self.calendar.handler_block (self.day_selected_double_handle)
                self.button.handler_block (self.clicked_handle)
                self.entry.handler_block (self.activate)
                self.entry.handler_block (self.focus_out)
       
        def __unblock_signals (self):
                #self.calendar.handler_unblock (self.day_selected_handle)
                self.calendar.handler_unblock (self.day_selected_double_handle)
                self.button.handler_unblock (self.clicked_handle)
                self.entry.handler_unblock (self.activate)
                self.entry.handler_unblock (self.focus_out)
       
        def get_text (self):
                return self.entry.get_text ()
       
        def set_date (self, date):
                if not date:
                        date = datetime.datetime.fromtimestamp (time.time())
                self.currentDate = date
                self.__block_signals ()
                self.calendar.select_day (1)
                self.calendar.select_month (self.currentDate.month-1, self.currentDate.year)
                self.calendar.select_day (self.currentDate.day)
                self.__unblock_signals ()
                self.update_entry ()

        def get_date (self):
                return self.currentDate

        def hide_widget (self, *args):
                self.cwindow.hide_all ()
		self.update_entry ()

        def show_widget (self, *args):
                self.cwindow.show_all ()

        def update_entry (self, *args):
                year,month,day = self.calendar.get_date ()
                month = month + 1;
		if (self.time.get_text () > ''):
			hour,minute = string.split (self.time.get_text (), ':')
		else:
		  	hour,minute = [0,0]
                self.currentDate = datetime.datetime(year, month, day, int (hour), int (minute))
                self.entry.set_text (self.currentDate.strftime ("%D"))
                self.emit ('changed', self.currentDate)

        def update_calendar (self, *args):
                try:
                        dt = datetime.datetime.strptime (self.entry.get_text (), "%d/%m/%Y")
                except:
                        try:
                                dt = datetime.datetime.strptime (self.entry.get_text (), "%d/%m/%y")
                        except:
                                print 'CalendarEntry.update_calendar: Error parsing date, setting it as today...'
                                dt = datetime.date.fromtimestamp(time.time())
                       
                self.set_date (dt)
                self.hide_widget ()
       
        def focus_out_event (self, widget, event):
                self.update_calendar ()
                self.hide_widget ()
