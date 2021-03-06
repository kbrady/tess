# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename, get_session_names
# to calculate the standard deviation of dimensions
import numpy as np
# to copy files
from shutil import copyfile
# to record reading times in csv
import csv

def get_last_frame_files(sess, dir_name='last_frames', part='digital reading'):
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	if len(reading_times) == 0:
		return
	last_time = max(reading_times)
	# copy the hocr and image files from the last frame of this session to the directory
	path_to_hocr = sess.dir_name + os.sep + settings.global_id_dir + os.sep + time_to_filename(last_time, extension='hocr')
	path_to_image = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + time_to_filename(last_time, extension='jpg')
	sess_name = sess.id
	# make the dirrectory if it doesn't exits
	if not os.path.isdir(dir_name):
		os.mkdir(dir_name)
	# copy the files
	copyfile(path_to_hocr, dir_name + os.sep + sess_name + '.hocr')
	copyfile(path_to_image, dir_name + os.sep + sess_name + '.jpg')

def get_reading_times():
	all_sesion_names = get_session_names()

	all_times = []
	for sess_name in all_sesion_names:
		sess = Session(sess_name)
		reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
		if len(reading_times) == 0:
			start_time = None
			end_time = None
		else:
			start_time = min([x['start_time'] for x in reading_times])
			end_time = max([x['end_time'] for x in reading_times])
		all_times.append([sess_name, start_time, end_time])
	with open('reading_times.csv', 'w') as outfile:
		writer = csv.writer(outfile)
		writer.writerow(['sess_name', 'start_time', 'end_time'])
		for row in all_times:
			writer.writerow(row)

for sess_name in os.listdir('data'):
	if sess_name.startswith('.') or sess_name.endswith('.zip') or sess_name.endswith('.txt') or sess_name == '4657':
		continue
	print(sess_name)
	sess = Session(sess_name)
	get_last_frame_files(sess)