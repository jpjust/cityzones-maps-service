#
# Regular cron jobs for the cityzones-maps-service package
#
0 4	* * *	root	[ -x /usr/bin/cityzones-maps-service_maintenance ] && /usr/bin/cityzones-maps-service_maintenance
