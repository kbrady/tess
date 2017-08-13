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

"""
This file calculates some statistics which we cite in grants and papers
such as the number of fixations per session.
"""

def count_fixations(filename):
	time_count = 0
	measurement_count = 0
	with open(filename, 'r') as input_file:
		reader = csv.reader(input_file, delimiter='\t')
		line_obj = None
		for row in reader:
			if line_obj is None:
				if len(row) < 10:
					continue
				header = list(row[:30])
				for i in range(len(header)):
					if re.match('[^a-zA-Z].*', header[i]):
						header[i] = 'a'+header[i]
					header[i] = header[i].replace(' ','_')
					header[i] = header[i].replace('#','_')
					header[i] = header[i].replace('-','_')
				line_obj = namedtuple('LineObj', header)
				continue
			row = line_obj(*tuple(row[:30]))
			time_count += 1
			measurement_count += 1 if row.GazeX not in [-1,'','-1'] else 0
	return measurement_count, time_count

def get_fixation_stats():
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
			students[sess_name] = count_fixations(path + os.sep + filename)
	return students

def average_fixations(sess_name_filter=lambda x: re.match('[0-9][0-9][0-9][0-9]', x)):
	students = get_fixation_stats()
	student_values = [students[k] for k in students.keys() if sess_name_filter(k)]
	measurements, attempts = zip(*student_values)
	total_measurments = sum(measurements)
	total_attempts = sum(attempts)
	print 'fixation measurements per session', float(total_measurments)/len(student_values)
	print 'percent of attempted measurements successful', float(total_measurments)/total_attempts
	print 'min fixations', min(measurements)
	print 'max fixations', max(measurements)

average_fixations()
