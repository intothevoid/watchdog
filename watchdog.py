#!/usr/bin/env python

import os
from os import system
from urllib2 import urlopen
from socket import socket
from sys import argv
import subprocess
import ConfigParser
import time
import logging

#For logging
logger = None
g_logfile = 'watchdog.log'
g_cfgfile = 'settings.cfg'


def usage():
	print('Correct usage watchdog.py <no-args-supported yet>')


#Function to perform basic TCP check by connecting on specified port
def tcp_test(server_info):
	cpos = server_info.find(':')
	try:
		sock = socket()
		sock.settimeout(10)
		sock.connect((server_info[:cpos], int(server_info[cpos+1:])))
		sock.close()
		return True
	except:
		return False


#Function to perform HTTP URL open check
def http_test(server_info):
	try:
		data = urlopen(server_info).read()
		return True
	except:
		return False


#Wrapper for above connection functions
def server_test(test_type, server_info):
	if test_type.lower() == 'tcp':
		return tcp_test(server_info)
	elif test_type.lower() == 'http':
		return http_test(server_info)

#Check if specified service is running. Restart if needed
def service_check(service_name, restart):
	output = subprocess.check_output(['ps', '-A'])
	if service_name in output:
		return True
	else:
		#Try to restart
		if restart:
			logger.warning('Trying to restart %s' % (service_name))
			system('service %s start' % (service_name))
		return False


#Check disk space usage. Return percentage
def du_check():
	df = os.popen("df -h /dev/sda1 | awk 'NR > 1 {print (100 - $5)}'")
	space = df.read()
	return space


#Get CPU usage
def getCPUAvg():
	try:
		cpuload = os.getloadavg()[2]
	except OSError, e:
		logger.error('Exception:Unable to obtain CPU load average.')
	return cpuload


#Send an error email to emails specified in configuration file
def send_error(test_type, server_info, email_address, message):
	footer = config.get('alerts','footer')
	cpuload = float(getCPUAvg())
	freespace = int(du_check())
	resource = 'Freespace: %s percent. CPU Load Avg (15 mins): %s percent.' % (freespace, cpuload)
	body = '[' + time.asctime() + '] ' + message + '\n\n' + resource + '\n\n' + footer
	subject = '[Error] %s %s' % (test_type.upper(), server_info)
	emailon = config.getboolean('alerts','emailon')

	#Update alert count
	alertcnt = int(config.get('appsettings','alerts'))
	config.set('appsettings', 'alerts', (alertcnt + 1))
	with open(g_cfgfile, 'wb') as configfile:
		config.write(configfile)

	#Respect max alerts per day
	alertcnt = int(config.get('appsettings','alerts'))
	maxalerts = int(config.get('alerts','maxdailyalerts'))

	#Only send email if enabled
	if alertcnt <= maxalerts:
		if True == emailon:
			system('echo "%s" | mail -s "%s" %s' % (body, subject, email_address))
			logger.info('Sent email. Content:%s' % (body))
	else:
		logger.warning('Maximum threshold for daily alerts has been reached.')


#Logging setup
def logsetup():
	global logger
	logger = logging.getLogger('watchdog')
	hdlr = logging.FileHandler(g_logfile)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.setLevel(logging.INFO)

def resetalertcount():
	#doy = day of year
	today_doy = int(time.localtime().tm_yday)
	lastrun_doy = int(config.get('appsettings', 'lastrun'))

	#If day has changed, update alert count
	if today_doy != lastrun_doy:
		config.set('appsettings', 'alerts', 0)
		with open(g_cfgfile, 'wb') as configfile:
			config.write(configfile)


#Main function
if __name__ == '__main__':
	#Initial test type
	testtype = 'tcp'

	#Read configuration
	config = ConfigParser.RawConfigParser()
	config.read(g_cfgfile)

	#Reset alert count if day has changed
	resetalertcount()

	#Update lastrun timestamp (day in year 0 - 366)
	lastday = int(time.localtime().tm_yday)
	config.set('appsettings', 'lastrun', lastday)
	with open(g_cfgfile, 'wb') as configfile:
		config.write(configfile)

	#Setup log
	logon = config.getboolean('alerts','loggingon')
	logsetup()

	#Disable logging if not needed
	if False == logon:
		logger.disabled = True

	#Email addresses to send
	emailaddr = config.get('alerts', 'recplist')

	#Description tag
	desc = 'watchdog script report'

	#Do argument vector check
	if len(argv) != 1:
		print('Wrong number of arguments provided')
		usage()

	#Do TCP connection check
	if not server_test(testtype, tcpurl):
		logger.error('Unable to connect to the specified server')
		send_error(testtype, tcpurl, emailaddr, "Failed to connect to server")

	#Do HTTP URL open connection check
	testtype = 'http'
	if not server_test(testtype, httpurl):
		logger.error('Failed to receive HTTP reply from specified server')
		send_error(testtype, tcpurl, emailaddr, "Failed to receive HTTP reply from Server.")

	#Services running check
	svcstr = config.get('services', 'list')
	brestart = config.getboolean('services','restart')
	services = svcstr.split(',')

	for currsvc in services:
		testtype = currsvc
		if not service_check(currsvc, brestart):
			err_msg = '%s service is not running or has crashed.' % (currsvc)
			logger.error(err_msg)
			send_error(testtype, desc, emailaddr, err_msg)

	#Disk usage check
	testtype = 'diskusage'
	space = int(du_check())
	threshold = int(config.get('diskspace','threshold'))
	message = ('Freespace threshold reached. %s percent freespace left.' % int(space))
	if space < threshold:
		logger.error(message)
		send_error(testtype, desc, emailaddr, message)

	#CPU Usage check - Greater than 50% in last 15 mins
	testtype = 'cpuusage'
	avgload = float(getCPUAvg())
	message = ('CPU usage critical. Usage: %s.' % float(avgload))
	if avgload >  float(50.0):
		logger.error(message)
		send_error(testtype, desc, emailaddr, message)
