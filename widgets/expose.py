#!/usr/bin/python
#
# Exposure script. Send exposure command on API, get back image.
#
# (C) 2011 Petr Kubanek, Institute of Physics <kubanek@fzu.cz>

import login

if __name__ == '__main__':
	l = login.Login()
	l.signon ()

	login.getProxy().executeCommand('C0','expose')
