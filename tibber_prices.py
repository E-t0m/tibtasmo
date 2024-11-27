#!/usr/bin/python3
# -*- coding: utf-8 -*-
debug = False

from json import load as json_load
from json import dump as json_dump
from time import strftime
from datetime import timedelta, datetime
from os.path import abspath, join, dirname
import syslog

today_present = False; today_date = None
tomorrow_present = False; tomorrow_date = None
today = datetime.now().strftime('%Y-%m-%d')

try:
	with open(join(dirname(__file__),'tibber_prices.json'),'r') as fi:
		tibber_response = json_load(fi)		# read known prices from file
except:
	if debug: print('error reading: tibber_prices.json')
else:
	try:
		if len(tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']) == 24:
			today_present = True
			today_date = tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today'][0]['startsAt'][0:10]
			if debug: print('today data is available:',today_date)
	except: pass
	try:
		if len(tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow']) == 24:
			tomorrow_present = True
			tomorrow_date = tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow'][-1]['startsAt'][0:10] 
			if debug: print('tomorrow data is available:',tomorrow_date)
	except: pass

if datetime.now().hour < 13:
	if 	( today_present 	and today_date		== today ) or \
		( tomorrow_present	and tomorrow_date	== today ):
		if debug: print('tomorrow data is not yet available\ndone.')
		exit(0)
else:
	if 	( today_present 	and today_date		== today ) and \
		( tomorrow_present	and tomorrow_date	== (datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d') ):
		if debug: print('done.')
		exit(0)

# fetch new prices from server
import requests
query = """
{	viewer {
	homes {
	currentSubscription {
		priceInfo {
		today {
			total
			startsAt }
		tomorrow {
			total
			startsAt }
}}}}}	"""
try:
	with open(join(dirname(__file__),'tibber_personal_token.json'),'r') as fi: 
		tibber_personal_token = json_load(fi)['tibber_personal_token']	# get personal token from file
except:
	if debug: print('error reading: tibber_personal_token.json')
	syslog.syslog(syslog, "error reading: tibber_personal_token.json")
	exit(1)
else:
	if debug: print('successful read: tibber_personal_token.json')

if debug: print('fetching data from server:')
tibber_response = requests.post( "https://api.tibber.com/v1-beta/gql", json={"query":query}, headers={"Authorization":'Bearer ' + tibber_personal_token, "Content-Type": "application/json"} ).json()

if debug: print(tibber_response)

if 'Response \[200\]' in tibber_response:
	if debug: print('<Response [200]> from server, try again later')
	syslog.syslog(syslog.LOG_INFO, "<Response [200]> from server")
	exit(1)

try:
	with open(join(dirname(__file__),'tibber_prices.json'),'w') as fo: json_dump(tibber_response,fo)	# write response to file
except:
	if debug: print('error writing: tibber_prices.json')
	syslog.syslog(syslog, "error writing: tibber_prices.json")
	exit(1)

if debug: print('done.')
syslog.syslog(syslog.LOG_INFO, "price data updated")
exit(0)
