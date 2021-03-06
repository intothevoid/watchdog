watchdog - automated web server monitoring
==========================================

Python script for Linux to watch various params of a web server and email reports.

Features -

1. Logging
2. Email reports in case of any alerts
3. Configure params to monitor via a configuration file
4. Monitor CPU usage of web server
5. Monitor disk usage of web server
6. Monitor various services (such as Apache, MySQL etc.) with ability to restart
7. Ability to set max no. of alerts per day to prevent flooding email inbox
8. TCP call to webservice or host with port
9. HTTP call for website availability check

Note:

1. Works only on Linux (Use shell calls to disk usage 'df' and 'ps -A' etc.)
2. Sendmail needs to be configured for correct email send functionality
3. For correct functioning add a cron job which executes the script approx. every 5 mins depending on frequency
