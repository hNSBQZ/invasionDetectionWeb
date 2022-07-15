import os

import fcntl
import pandas as pd


def stage(t):
	if t in range(1,7):
		return '凌晨'
	elif t in range(7,12):
		return '上午'
	elif t in range(12,18):
		return '下午'
	else:
		return '晚上'

def stage2(t):
	if 0 <= t < 4:
		return '0~4点'
	elif 4 <= t < 8:
		return '4~8点'
	elif 8 <= t < 12:
		return '8~12点'
	elif 12 <= t < 16:
		return '12~16点'
	elif 16 <= t < 20:
		return '16~20点'
	else:
		return '20~24点'


#生成数据
def mian():
	try:
		os.remove('log_statistic.txt')
	except:
		print('no this file')
	with open('log.txt', 'r') as f1:
		with open('log_statistic.txt', 'a') as f2:
			fcntl.flock(f1.fileno(), fcntl.LOCK_EX)
			line = f1.readline()
			f2.write(line)
			while line:
				line = f1.readline()
				f2.write(line)
	data_rows = pd.read_csv('log_statistic.txt',sep=' ',names=['date','time','object','level'])
	data_rows['hour'] = data_rows['time'].apply(lambda x:x.split('_')[0])
	data_rows['d'] = data_rows['date'].apply(lambda x:x.split('-')[-2]+'/'+x.split('-')[-1])
	return data_rows

# 折线图
def date_count():
   data_rows = mian()
   date_count = data_rows.groupby('date').count()['hour'].to_dict()
   x = list(date_count.keys())
   y = list(date_count.values())
   return x, y

def numberset(numd):
	if numd == '0~4点':
		return 0
	if numd == '4~8点':
		return 1
	if numd == '8~12点':
		return 2
	if numd == '12~16点':
		return 3
	if numd == '16~20点':
		return 4
	if numd == '20~24点':
		return 5

#雷达图
def leida():
	data_rows = mian()
	datanew = []
	datenum = 0
	data_rows['stage'] = data_rows['hour'].apply(lambda x : stage2(int(x)))
	for i in data_rows['stage']:
		number_set = numberset(i)
		datenum += 1
		if number_set == 0:
			datanew = [datenum, 0, 0, 0, 0, 0]
		elif number_set == 1:
			datanew = [0, datenum, 0, 0, 0, 0]
		elif number_set == 2:
			datanew = [0,  0, datenum, 0, 0, 0]
		elif number_set == 3:
			datanew = [0,  0, 0, datenum, 0, 0]
		elif number_set == 4:
			datanew = [0,  0, 0, 0,datenum, 0]
		elif number_set == 5:
			datanew = [0,  0, 0, 0, 0, datenum]
	return datanew
