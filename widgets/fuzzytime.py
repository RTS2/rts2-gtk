"""Display fuzzy time - e.g. 2m instead of 120 sec,.."""
#
# Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import gettext

t = gettext.translation('rts2',fallback=True)
_ = t.lgettext

def fuzzy_delta(t):
	"""Time in seconds"""
	# possible values, with divider to check for them
	ret = ''
	if t < 0:
		ret = '-'
		t = -1 * t

	values = [[_('days'),86400.0],[_('h'),3600],[_('m'),60]]
	added = False

	for x in values:
	  	d = t / x[1]
		if int(d) != 0:
		  	if added:
				ret += ' '
			else:
				added = True  	
			ret += '{0}{1}'.format(int(d),x[0])
		t %= x[1]

	if t > 0:
		if added:
			ret += ' '
		ret += '{0}s'.format(int(t))

	return ret	
