#!/usr/bin/env python3
from json import load as json_load
from os.path import abspath, join, dirname
from datetime import datetime
from requests import get
import syslog

tasmota_dev =	{	'auto1':{'ip':'192.168.178.88','timer_id': '1','output':'1'}, \
					'auto2':{'ip':'192.168.178.88','timer_id': '2','output':'2'}	}
debug = False

def tasmota_timer(dev,time,action):
	return( get('http://'+dev['ip']+'/cm?cmnd=Timer'+dev['timer_id']+'{\"Enable\":1,\"Mode\":0,\"Time\":\"'+time+'\",\"Window\":\"0\",\"Days\":\"SMTWTFS\",\"Repeat\":0,\"Output\":'+dev['output']+',\"Action\":'+action+'}' ) )

def tasmota_switch(dev,action):
	return( get('http://'+dev['ip']+'/cm?cmnd=Power'+dev['output']+'%20'+action ) )

def main():
	prices = dict()
	with open(join(dirname(__file__),'tibber_prices.json'),'r') as fi:	tibber_response = json_load(fi) 		# read known prices from file
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']:	prices[i['startsAt'][0:13]] = i['total']
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow']:	prices[i['startsAt'][0:13]] = i['total']
	
	price_avg = sum(prices.values())/len(prices)*100
	price_min = min(prices.values())
	price_max = max(prices.values())
	price_spread = (price_max-price_min)*100
	price_lt = price_avg - (price_spread / 5)
	price_ut = price_avg + (price_spread / 5)
	
	if debug:	print('avg: %.2f'%price_avg,'min: %.2f'%(100*price_min),'max: %.2f'%(100*price_max),'spread: %.2f'%price_spread,'lt: %.2f'%price_lt,'ht: %.2f'%price_ut)
	
	hour_now = datetime.now().strftime('%Y-%m-%dT%H')
	output_on = False
	timer_is_set = False
	
	for i in range(0,len(prices.values())):
		
		cur_p_time = list(prices.keys())[i]
		cur_timer = cur_p_time[-2:]+':00'
		cur_price = prices[cur_p_time]*100
		msg = ''
		
		if datetime.strptime(cur_p_time+':59:59', '%Y-%m-%dT%H:%M:%S') < datetime.now(): continue
		
		if   cur_price < price_lt: 
			p_char = '+'
			
			if hour_now == cur_p_time:
				if output_on: pass 
				else:
					msg += ' hot switch on'
					output_on = True
					msg += ' 1' if tasmota_switch( tasmota_dev['auto1'],'1').status_code == 200 else ' ¹'
					msg += ' 2' if tasmota_switch( tasmota_dev['auto2'],'1').status_code == 200 else ' ²'
					syslog.syslog(syslog.LOG_INFO, msg)
			else:
				if output_on: pass
				else:
					msg += ' set timer on:'
					output_on = True
					if not timer_is_set:
						timer_is_set = True
						msg += ' 1' if tasmota_timer( tasmota_dev['auto1'],cur_timer,'1').status_code == 200 else ' ¹'
						msg += ' 2' if tasmota_timer( tasmota_dev['auto2'],cur_timer,'1').status_code == 200 else ' ²'
						syslog.syslog(syslog.LOG_INFO, msg +' at '+ cur_timer)
		else: 
			p_char = '.'
			if output_on:
				msg += ' set timer off'
				output_on = False
				if not timer_is_set:
					timer_is_set = True
					msg += ' 1' if tasmota_timer( tasmota_dev['auto1'],cur_timer,'0').status_code == 200 else ' ¹'
					msg += ' 2' if tasmota_timer( tasmota_dev['auto2'],cur_timer,'0').status_code == 200 else ' ²'
					syslog.syslog(syslog.LOG_INFO, msg +' at '+ cur_timer)
		
		if debug: print(str(msg).ljust(20),cur_p_time,'%2.2f'%cur_price,str(p_char).rjust(int(cur_price)))
	if debug: print('done.')
	return(0)

main()
exit(0)

