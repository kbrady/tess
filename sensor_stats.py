# to read sensor files
import csv
# to find files
import settings
# to search paths
import os
# to keep track of feild names
from collections import namedtuple
# to match session names
import re
# to calculate some stats
import numpy as np
# to visualize stats
from matplotlib import pyplot as plt

"""
This file calculates some statistics which we cite in grants and papers
such as the number of fixations per session.
"""

def steralize_header(header):
	new_header = []
	for val in header:
		val = re.sub("[^a-zA-Z0-9]", "_", val)
		if not re.match("[a-zA-Z]", val[0]):
			val = "a_" + val
		if val in new_header:
			counter = 0
			while val + "_"+str(counter) in new_header:
				counter += 1
			val += "_"+str(counter)
		new_header.append(val)
	return new_header

def get_data(filename):
	data = []
	with open(filename, 'r') as input_file:
		reader = csv.reader(input_file, delimiter='\t')
		line_obj = None
		for row in reader:
			if line_obj is None:
				if len(row) < 10:
					continue
				header = steralize_header(list(row))
				line_obj = namedtuple('LineObj', header)
				continue
			row = line_obj(*tuple(row))
			data.append(row)
	return data

def count_fixations(filename):
	data = get_data(filename)
	time_count = len(data)
	measurement_count = len([x for x in data if x.GazeX not in [-1,'','-1']])
	return measurement_count, time_count

def get_fixation_stats(stat_fun):
	students = {}
	for foldername in settings.raw_dirs:
		if not foldername.endswith(os.sep):
			foldername += os.sep
		path = foldername + 'Sensor_Data'
		for filename in os.listdir(path):
			# sometimes extra files get put in the Sensor Data folder
			if not filename.endswith('.txt') or not filename.startswith('Dump'):
				continue
			sess_name = filename[len('Dump')+4:filename.find('.txt')]
			students[sess_name] = stat_fun(path + os.sep + filename)
	return students

def average_fixations(sess_name_filter=lambda x: re.match('[0-9][0-9][0-9][0-9]', x)):
	students = get_fixation_stats(count_fixations)
	student_values = [students[k] for k in students.keys() if sess_name_filter(k)]
	measurements, attempts = zip(*student_values)
	total_measurments = sum(measurements)
	total_attempts = sum(attempts)
	print 'fixation measurements per session', float(total_measurments)/len(student_values)
	print 'percent of attempted measurements successful', float(total_measurments)/total_attempts
	print 'min fixations', min(measurements)
	print 'max fixations', max(measurements)

def find_windows(filename):
	data = get_data(filename)
	timepoints = [int(x.MediaTime) for x in data if x.MediaTime not in ['', '-1', -1]]
	windows = [timepoints[i+1]-timepoints[i] for i in range(len(timepoints)-1)]
	return windows

def ms_per_fixation(sess_name_filter=lambda x: re.match('[0-9][0-9][0-9][0-9]', x)):
	students = get_fixation_stats(find_windows)
	student_values = [students[k] for k in students.keys() if sess_name_filter(k)]
	all_windows = [x for l in student_values for x in l] # if x < 100]
	cuttoff = 100
	under_cuttoff = [x for x in all_windows if x < cuttoff]
	print 'frac. lower than', cuttoff, ':', float(len(under_cuttoff))/len(all_windows)
	plt.hist(under_cuttoff)
	plt.show()
	print 'frac. lower than', 10, ':', float(len([x for x in under_cuttoff if x < 10]))/len(all_windows)
	print 'average gap', np.mean(under_cuttoff)
	print 'median gap', np.median(under_cuttoff)
	print 'gap std', np.std(under_cuttoff)

if __name__ == '__main__':
	ms_per_fixation(sess_name_filter=lambda x : True)
