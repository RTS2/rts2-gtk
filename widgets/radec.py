#
# Module for drawing Ra Dec entry box
#
# Copyright (C) 2009 Petr Kubanek <petr@kubanek.net>

import string
import math

def to_hms(val): 
    """Return tuple containing sign, hours, minutes and seconds."""
    val = float(val)
    if (val < 0):
        val = abs(val)
	sign = '-'
    else:
	sign = '+'

    d = int(val)
    val = (val - d)* 60
    m = int(val)
    s = (val - m)*60
    ss = "%06.3f" % s
    if (ss[0] == '6'):
       m+=1
       s=0
    if (m == 60):
       d+=1
       m=0
    return (sign, d, m, s)

def from_hms(val):
    """Parse string containing HMS separated by : or whitespaces."""
    value = 0
    tv = ""
    div = 1
    sign = 1
    if val[0] == '+' or val[0] == '-':
       if val[0] == '-':
	 sign = -1
       val = val[1:]
    for c in val:
       if (c == ':' or c == ' '):
          value += float(tv) / div
	  tv = ""
	  div *= 60
       elif ((c >= '0' and c <= '9') or (c == '.') or (c == ',')):
          tv += c
       else:
	  raise ValueError
    if (tv != ""):
    	value += float(tv) / div
    return value*sign

def ra_string(ra, sep=':'):
    """Format RA as string."""
    if ra is None or math.isinf(ra):
        return "--:--:--.---"
    ra /= 15.0
    (sign,rah,ram,ras) = to_hms(ra)
    return (("%02i" + sep + "%02i" + sep + "%06.3f") % (rah, ram, ras))

def dec_string(dec, sep=':'):
    """Format DEC as string."""    
    if dec is None or math.isinf(dec):
         return "---:--'--.---\""
    (sign,dech,decm,decs) = to_hms(dec)
    return (("%s%02i" + sep + "%02i" + sep + "%05.2f") % (sign,dech, decm, decs))

def dist_string(dist):
    """Return string representing distance. Dist is in acrseconds."""
    ret = ''
    if dist >= 3600:
        ret += u'{0}\u00b0'.format(int(dist/3600))
    	dist %= 3600
    if dist >= 60:
        ret += u'{0}\u2032'.format(int(dist/60))
	dist %= 60
    if dist > 0:
        ret += u'{0}\u2033'.format(dist)
    return ret
