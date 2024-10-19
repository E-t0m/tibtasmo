#!/usr/bin/env python3
from json import load as json_load
from os.path import abspath, join, dirname
from datetime import datetime, timedelta
from requests import get
from sys import argv
import syslog

tasmota_dev =	{	'auto1_on':{'ip':'192.168.178.88','timer_id': '1','output':'1'}, \
					'auto2_on':{'ip':'192.168.178.88','timer_id': '2','output':'2'},
					'auto1_off':{'ip':'192.168.178.88','timer_id': '3','output':'1'},
					'auto2_off':{'ip':'192.168.178.88','timer_id': '4','output':'2'},
				}

verbose = True if '-v' in argv else False

def tasmota_timer(dev,time,action):
	try:
		res = get('http://'+dev['ip']+'/cm?cmnd=Timer'+dev['timer_id']+'{\"Enable\":1,\"Mode\":0,\"Time\":\"'+time+'\",\"Window\":\"0\",\"Days\":\"SMTWTFS\",\"Repeat\":0,\"Output\":'+dev['output']+',\"Action\":'+action+'}' ).status_code
	except:
		res = 1
	return(res)

def tasmota_switch(dev,action):
	try:
		res = get('http://'+dev['ip']+'/cm?cmnd=Power'+dev['output']+'%20'+action ).status_code
	except:
		res = 1
	return(res)

def main():
	prices = dict()
	with open(join(dirname(__file__),'tibber_prices.json'),'r') as fi:	tibber_response = json_load(fi) 	# read known prices from file
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']:	prices[i['startsAt'][0:13]] = i['total']
	for i in tibber_response['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow']:	prices[i['startsAt'][0:13]] = i['total']
	
	price_avg = 0
	future_prices = dict()							# prices to come
	for i in prices:
		if datetime.now() < datetime.strptime(i+':59:59', '%Y-%m-%dT%H:%M:%S'):
			price_avg += prices[i]
			future_prices[i] = prices[i]
	
	price_avg = price_avg / len(future_prices) *100
	price_min = min(future_prices.values())
	price_max = max(future_prices.values())
	price_spread = (price_max-price_min)*100
	price_lt = price_avg - (price_spread / 4 )		# set the divider to your needs
	price_ut = price_avg #(price_spread / 15 )		# it sets the threshold for the timers
	price_lt_max = 22								# in ¢, fixed maximum for timer activation
	
	if verbose:	print('avg: %.2f'%price_avg,'min: %.2f'%(100*price_min),'max: %.2f'%(100*price_max),'spread: %.2f'%price_spread,'lt: %.2f'%price_lt,'ht: %.2f'%price_ut)
	if price_lt > price_lt_max: 
		price_lt = price_lt_max
		if verbose: print('set lt to max: %.2f'%price_lt)
	
	tib_hour_now = datetime.now().strftime('%Y-%m-%dT%H')
	timer_is_set = [False]*(len(tasmota_dev)+1) 	# ignore index 0
	zerotimer = dict()
	hot_on = True								# True disables hot switching!
	hot_off = True
	
	for cur_p_time in prices:
		
		cur_price = prices[cur_p_time]*100
		cur_timer = cur_p_time[-2:]+':00'
		p_hour_is_cur = True if tib_hour_now == cur_p_time else False
		msg = 'now ' if tib_hour_now == cur_p_time else ' '
		past_time = False if cur_p_time in future_prices else True
		
		if past_time:
			if not verbose: continue
			p_char = 'o'
		else:										# current and future hours
			
			if cur_price < price_lt: 				# lower threshold
				p_char = '>'
				msg = '  '+msg
				
				if p_hour_is_cur:
					if hot_on: pass 
					else:
						msg += 'hot on:'
						hot_on = True
						msg += ' 1' if tasmota_switch( tasmota_dev['auto1_on'],'1') == 200 else ' 1FAIL'
						msg += ' 2' if tasmota_switch( tasmota_dev['auto2_on'],'1') == 200 else ' 2FAIL'
						if not verbose: syslog.syslog(syslog.LOG_INFO, msg)
				else:
					if not timer_is_set[1] and not timer_is_set[2]:
						msg += ' T on:'; timer_is_set[1] = True; timer_is_set[2] = True
						msg += ' 1' if tasmota_timer( tasmota_dev['auto1_on'],cur_timer,'1') == 200 else ' 1FAIL'
						msg += ' 2' if tasmota_timer( tasmota_dev['auto2_on'],cur_timer,'1') == 200 else ' 2FAIL'
						if not verbose: syslog.syslog(syslog.LOG_INFO, msg +' at '+ cur_timer)
				
			
			else:									# middle and upper
				p_char = '|'
				msg = '  '+msg
				
				if p_hour_is_cur:
					if hot_off: pass 
					else:
						msg += 'hot off:'
						hot_off = True
						msg += ' 1' if tasmota_switch( tasmota_dev['auto1_off'],'0') == 200 else ' 1FAIL'
						msg += ' 2' if tasmota_switch( tasmota_dev['auto2_off'],'0') == 200 else ' 2FAIL'
						if not verbose: syslog.syslog(syslog.LOG_INFO, msg)
				else:
					if not timer_is_set[3] and not timer_is_set[4]:
						msg += 'T off:'; timer_is_set[3] = True; timer_is_set[4] = True
						msg += ' 3' if tasmota_timer( tasmota_dev['auto1_off'],cur_timer,'0') == 200 else ' 3FAIL'
						msg += ' 4' if tasmota_timer( tasmota_dev['auto2_off'],cur_timer,'0') == 200 else ' 4FAIL'
						if not verbose: syslog.syslog(syslog.LOG_INFO, msg +' at '+ cur_timer)
				
				if price_ut < cur_price:			# upper threshold
					p_char = '<'
					if not past_time:
						msg = 'Z '+msg
						zerotimer[cur_p_time] = cur_price	# current hour will be enabled in the timerfile
			
		
		if verbose: print(str(msg).ljust(20),cur_p_time,'%2.2f'%cur_price,str(p_char).rjust(int(cur_price)))
	
	
	# write a timer file for zeroinput? set True or False below
	if True: 
		with open('/home/vzlogger/timer.txt','w') as fo:
			fo.write('# 0000-00-00 for daily repeating, space or tab separated\n#                   battery discharge W if > 100, percentage if <= 100\n# date     time     |   ac inverter power W if > 100, percentage if <= 100\n') #fileheader
			for tib_form in future_prices:
				file_form = tib_form.replace('T',' ') + ':00:00 ' + ('100 100' if tib_form in zerotimer else '0 0')
				fo.write(file_form+'\n')
				if '-vt' in argv : print(file_form)		# console output with -vt
	
	return(0)

main()
if verbose: print('done.')
exit(0)
