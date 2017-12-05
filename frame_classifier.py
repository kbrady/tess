# to get session info
from video_to_frames import Session, time_to_filename, get_session_names
# to get local settings
import settings
# to navigate files
import os
# for making and reading images
from matplotlib import pyplot as plt
from scipy import misc
# to manipulate images
import numpy as np

def get_transition_pairs(reading_data):
	all_times = reading_data['transitions']
	all_times.sort()
	return zip(all_times[:-1], all_times[1:])

def get_image(sess, time):
	image_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + time_to_filename(time)
	return misc.imread(image_path)

def transition_difference(sess, pair):
	im1 = get_image(sess, pair[0])
	im2 = get_image(sess, pair[1])
	trans_diff = im1 - im2
	dir_name = sess.dir_name + os.sep + settings.transition_images
	if not os.path.isdir(dir_name):
		os.mkdir(dir_name)
	filename = dir_name + os.sep + time_to_filename(pair[0])
	misc.imsave(filename, trans_diff)

def get_image_differences(sess):
	all_transitions = []
	for data in sess.metadata:
		if data['part'] == 'digital reading':
			all_transitions += get_transition_pairs(data)
	for t in all_transitions:
		transition_difference(sess, t)

if __name__ == '__main__':
	all_sessions = get_session_names()
	for sess_name in all_sessions:
		get_image_differences(Session(sess_name))