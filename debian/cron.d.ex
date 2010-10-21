#
# Regular cron jobs for the pyweb package
#
0 4	* * *	root	[ -x /usr/bin/pyweb_maintenance ] && /usr/bin/pyweb_maintenance
