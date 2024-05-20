#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
from time import time, strftime, sleep
from datetime import datetime
from os.path import abspath, join, dirname

debug = False

prices = dict()
try:
	with open(join(dirname(__file__),'tibber_prices.json'),'r') as fi:	tibber_response = json.load(fi) 		# read known prices from file
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']:	prices[i['startsAt'][0:13]] = i['total']
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow']:	prices[i['startsAt'][0:13]] = i['total']
except: 
	if debug: print('error processing: tibber_prices.json')
	exit(1)

try:
	hpr = prices[datetime.now().strftime('%Y-%m-%dT%H')]
except:
	if debug: print('hour price not found!\nSTOP')
	exit(1)

for i in range(0,60):					# repeat 60 seconds
	ostr = '%i: tibber = %f\n'	% ( time(), hpr*100 )
	with open('/tmp/vz/soyo.log','a') as fo:	fo.write(ostr)
	if debug: print(i,ostr)
	sleep(1)

exit(0)
