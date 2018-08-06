# to read in the screen grab
import numpy as np
from scipy import misc
# to read the length of the video
import imageio
# to find files and run ffmpeg
import os
# to look in the right places
import settings
# to load and save metadata
import json
# to time how long everything is taking
import time
# for debugging
import sys
# to run ffmpeg in the background
import subprocess

# A class to keep track of a sessions files
class Session:
	def __init__(self, id_string, video_sub_dir=''):
		# this is the string by which this participant will be recognized by from now on
		self.id = id_string
		# make a data folder to put things in
		self.dir_name = settings.data_dir+self.id
		if not os.path.isdir(self.dir_name):
			os.mkdir(self.dir_name)
		# find the files among the raw data that were recorded for this session
		# add a subdirectory to look in if the program needs to look deeper (as in the iMotions data)
		self.screen_recording_filename = self.calculate_filenames(video_sub_dir)
		# load any metadata that exists
		self.metadata = []
		if os.path.exists(self.dir_name + os.sep + settings.metadata_file):
			with open(self.dir_name + os.sep + settings.metadata_file, 'r') as metadata_input:
				json_str = ' '.join([line for line in metadata_input])
				# sometimes the program gets interupted before a dump is complete
				if len(json_str) > 5:
					self.metadata = json.loads(json_str)
	
	# calculate the names of any files for this session
	def calculate_filenames(self, dir_name):
		output = []
		# look through the files in both conditions, this makes it easier than remember all the condition pairings
		for path_start in settings.raw_dirs:
			path = path_start + dir_name
			path = path if path.endswith(os.sep) else path + os.sep
			for filename in os.listdir(path):
				# sometimes the sensor data has a space between Dump_ and the session id
				filename_part = filename[filename.find('_')+1:].strip()
				if filename.find(self.id) > -1:
					output.append(path + filename)
		# it is posible that one participants id is a substring of another's so we should take the shortest filename
		output.sort(key=len)
		# exactly one file for each type should be found for each session
		if len(output) == 0:
			raise Exception(str(len(output))+' files found for '+self.id+': '+','.join(output))
		return output[0]
	
	# a handy function to see if we got all the raw data right
	def __repr__(self):
		return 'Session('+self.id+')'

	# A function to pull out the frame for a given time in the video
	# switch only_if_frame_does_not_exist on if the program might quit and need to start up again
	def screen_time_to_picture(self, current_time, only_if_frame_does_not_exist=True):
		# It is good to have this turned on if you think you will run this on the same time stamp without meaning to
		if only_if_frame_does_not_exist:
			if self.picture_for_frame_exists(current_time):
				return
		# make sure the time requested is valid
		duration = imageio.get_reader(self.screen_recording_filename, 'ffmpeg').get_meta_data()['duration']
		if current_time > duration:
			raise Exception('Time entered was greater than video length')
		# find the directory to put frames in and create one if it doesn't exist yet
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		if not os.path.isdir(dir_name):
			os.mkdir(dir_name)
		# turn the time into a filename of the correct format
		filename = time_to_filename(current_time)
		# in order to run this you'll need ffmpeg installed. I haven't found a good frame puller in python
		command = ['ffmpeg', '-ss']
		# calculate the minutes and seconds of the time
		minutes = int(current_time/60)
		seconds = current_time - (minutes * 60)
		command.append('00:'+num_to_str(minutes)+':'+num_to_str(seconds))
		command += ['-i', self.screen_recording_filename, '-frames:v', '1', dir_name+os.sep+filename]
		# Apparently Popen stops the python script after running
		subprocess.call(command)

	# a function to save time by not running ffmpeg more than necessary
	def picture_for_frame_exists(self, current_time):
		# if the directory doesn't exist, neither does any file in it
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		if not os.path.isdir(dir_name):
			return False
		filename = time_to_filename(current_time)
		return os.path.exists(dir_name + os.sep + filename)
	
	# pull out a frame at 10 second intervals (assumed to be small enough to catch changes)
	# this appears to be too short for pop-ups
	def break_into_chunks(self, chunk_size_in_seconds=10):
		duration = imageio.get_reader(self.screen_recording_filename, 'ffmpeg').get_meta_data()['duration']
		current_time = 0
		# pull out frames for every chunk_size_in_seconds seconds until the end of the video
		while current_time < duration:
			self.screen_time_to_picture(current_time)
			current_time += chunk_size_in_seconds

	# figure out which part of the stimuli the current frame belongs to
	# this uses a lot of hard coded methods of assessing whether the part is the same
	def assess_stimuli_timestamps(self, file_list=None):
		assignments = {}
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		if file_list is None:
			file_list = os.listdir(dir_name)
		for image_file in file_list:
			part_of_stimuli = figure_out_part_of_stimuli_frame_is_in(dir_name + os.sep + image_file)
			assignments[image_file] = part_of_stimuli
		return assignments

	# find reading transitions during the post test
	def find_form_reading_transitions(self):
		self.find_reading_transitions(part = 'form')

	def find_digital_reading_transitions(self):
		self.find_reading_transitions(part = 'digital reading')

	def find_reading_transitions(self, part='digital reading'):
		# calculate the metadata globally
		# this method is only for the digital reading so the rest of the session
		# should already be calculated
		if len(self.metadata) == 0:
			self.metadata = self.calculate_metadata(save_to_file=True)
		# get the time spans when digital reading occured
		reading_times = [x for x in self.metadata if x['part'] == part]
		# the directory where frames are stored
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		picture_value = lambda filename: get_part_of_picture(dir_name + os.sep + filename, x_range=settings.x_range[part], y_range=settings.y_range[part])
		for reading_interval in reading_times:
			filenames = self.get_image_filenames_in_timespan(reading_interval['start_time'], reading_interval['end_time'])
			for i in range(len(filenames)-1):
				# do a binary search between frames for the point of transition
				# the search will halt imediately if there is no difference
				start_value = picture_value(filenames[i])
				end_value = picture_value(filenames[i+1])
				start_time = filename_to_time(filenames[i])
				end_time = filename_to_time(filenames[i+1])
				self.binary_frame_search(start_time, end_time, start_value, end_value, value_fun=picture_value)
			# now that we have made sure we have all the necessary files, look for the transitions
			# recalculating this takes time but debugging the faster version will take time
			filenames = self.get_image_filenames_in_timespan(reading_interval['start_time'], reading_interval['end_time'])
			transition_list = [filename_to_time(filenames[0])]
			for i in range(len(filenames)-1):
				# figure out if two fames are the same
				start_value = picture_value(filenames[i])
				end_value = picture_value(filenames[i+1])
				if images_different(start_value, end_value):
					transition_list.append(filename_to_time(filenames[i+1]))
			reading_interval['transitions'] = transition_list
		with open(self.dir_name + os.sep + settings.metadata_file, 'w') as metadata_output:
			metadata_output.write(json.dumps(self.metadata, ensure_ascii=False))

	# get all frame images which have been taken in a given time span
	def get_image_filenames_in_timespan(self, start_time, end_time):
		output = []
		for filename in os.listdir(self.dir_name + os.sep + settings.frame_images_dir):
			time = filename_to_time(filename)
			if start_time <= time and time <= end_time:
				output.append(filename)
		output.sort(key = lambda x: filename_to_time(x))
		return output

	# this funciton calculates the metadata for this section
	# it can save the metadata to the metadata.json file so it can be accessed later
	def calculate_metadata(self, save_to_file=False):
		metadata = []
		assignments = self.assess_stimuli_timestamps()
		times = assignments.keys()
		times = [(filename_to_time(t), t) for t in times]
		times.sort()
		start_time = None
		# go through the existing frames in order to find the span of each type of interaction
		for i in range(len(times)):
			if i == 0:
				start_time = times[i][0]
				continue
			# record each time span
			if assignments[times[i-1][1]] != assignments[times[i][1]]:
				time_span = {}
				time_span['part'] = assignments[times[i-1][1]]
				time_span['start_time'] = start_time
				time_span['end_time'] = times[i-1][0]
				start_time = times[i][0]
				metadata.append(time_span)
		# record the final time span
		duration = imageio.get_reader(self.screen_recording_filename, 'ffmpeg').get_meta_data()['duration']
		time_span = {}
		time_span['part'] = assignments[times[-1][1]]
		time_span['start_time'] = start_time
		time_span['end_time'] = duration
		metadata.append(time_span)
		# save everything to the metadata file if the save flag is True
		if save_to_file:
			# set own metadata in case this has not been done
			self.metadata = metadata
			with open(self.dir_name + os.sep + settings.metadata_file, 'w') as metadata_output:
				metadata_output.write(json.dumps(metadata, ensure_ascii=False))
		# return the calculated metadata
		return metadata

	# this function finds the transitions between parts of the stimuli (like digital reading and forms)
	def find_transitions(self):
		assignments = self.assess_stimuli_timestamps()
		times = assignments.keys()
		times = [(filename_to_time(t), t) for t in times]
		times.sort()
		value_fun = lambda x: self.assess_stimuli_timestamps(file_list=[x])[x]
		# go through the existing frames in order to find transitions
		for i in range(len(times)-1):
			# do a binary search for every gap that is more than .1 seconds wide
			if assignments[times[i][1]] != assignments[times[i+1][1]]:
				if times[i+1][0] - times[i][0] <= .1:
					continue
				self.binary_frame_search(times[i][0], times[i+1][0], assignments[times[i][1]], assignments[times[i+1][1]], value_fun=value_fun)

	# this is a function to find points when the video changed using a binary search
	# This is used both to differentiate between parts of the stimuli (like digital reading and forms)
	# and between frames in the digital reading section
	def binary_frame_search(self, start_time, end_time, start_value, end_value, value_fun):
		# check if we should stop due to time
		if start_time > end_time or end_time - start_time <= .15:
			return
		# in some cases we compare whether the catagories of images
		# (figured out by the functions below) are the same
		# in other cases we want to check if the matracies representing the
		# images are the same
		if type(start_value) == str:
			key = lambda x, y: x == y
		else:
			key = lambda x, y: not images_different(x, y)
		# check if we should stop due to the values being equal
		if key(start_value, end_value):
			return
		middle_time = float(int((float(start_time + end_time)/2)*10))/10
		# might not actually get a middle time due to round off error
		if middle_time == start_time or middle_time == end_time:
			return
		#print((time_to_filename(start_time), time_to_filename(middle_time), time_to_filename(end_time)))
		middle_filename = time_to_filename(middle_time)
		self.screen_time_to_picture(middle_time)
		middle_value = value_fun(middle_filename)
		self.binary_frame_search(start_time, middle_time, start_value, middle_value, value_fun=value_fun)
		self.binary_frame_search(middle_time, end_time, middle_value, end_value, value_fun=value_fun)

# this function is used more than any other by other scripts
# from a timestamp calculate the filename
def time_to_filename(current_time, extension='jpg'):
	extension = extension.strip('.')
	# calculate the minutes and seconds of the time and use these values to create the filename
	minutes = int(current_time/60)
	seconds = float(current_time - (minutes * 60))
	filename = num_to_str(minutes)+'-'+num_to_str(seconds)+'.' + extension
	return filename

# from a filename calculate the timestamp
def filename_to_time(filename):
	parts = filename.split('.')
	minutes, seconds = [int(x) for x in parts[0].split('-')]
	if len(parts) > 2:
		miliseconds = float('.'+parts[1])
	else:
		miliseconds = 0
	return minutes * 60 + seconds + miliseconds

# calculate if two images are the same in a fast manner
# Ajay and I are going to work on an even better method which will 
# figure out forgrounds (pop-ups) and scrolling
def images_different(t1_img, t2_img):
	# helper function to load images
	def flatten_img(img):
		return img[:,:,0]/3 + img[:,:,1]/3 + img[:,:,2]/3
	# helpur function to get the difference between images
	def compare_images(t1_img, t2_img):
		diff = abs(flatten_img(t1_img) - flatten_img(t2_img))
		return diff
	# helper functon to do a recursive search and find box
	# we only need to find one box to consider images different, so
	# don't worry about figuring out where they are
	def find_box(mat, depth=0):
		# important constants based on search of best values for
		# splitting the images found for the seventh undergrad
		frac_for_diff = .9
		cutoff = 1
		# get the dimensions of the matrix part
		height, width = mat.shape
		# figure out if the stoping consitions are met
		num_above_cutoff = (mat > cutoff).sum()
		if float(num_above_cutoff)/mat.size > frac_for_diff:
			return True
		# if a box has less than 100 * frac_for_diff pixels which are different
		# it couldn't be mostly different anyway
		if num_above_cutoff.sum() < 100 * frac_for_diff:
			return False
		# if the size falls bellow double the height of text, we don't consider smaller windows
		if height < 20 and width < 20:
			return False
		# split mat in half
		mat_l = mat[:, :width/2]
		mat_r = mat[:, width/2:]
		# get results
		# transpose the matrix so next time we cut top to bottom
		left_diff = find_box(mat_l.T, depth + 1)
		# if we found a box on the left, don't bother looking on the right
		if left_diff:
			return left_diff
		right_diff = find_box(mat_r.T, depth + 1)
		return right_diff

	gray_diff_img = compare_images(t1_img, t2_img)
	
	return find_box(gray_diff_img)

# need to fix this function
def figure_out_part_of_stimuli_frame_is_in(image_path):
	# for now it is all typing
	return 'typing'
	pic = np.array(misc.imread(image_path))
	# cut off the top and bottom parts of the frame which show the address bar and the dock
	# cut off the right part of the frame which may be showing the note taking menu (not important for the moment)
	pic = pic[50:800, :900, :]
	if is_form(pic):
		return 'form'
	else:
		percent_white = image_has_color(pic, rgb=[255, 255, 255])
		if percent_white > .8:
			return 'paper or splash page'
		elif percent_white > .4:
			return 'digital reading'
		else:
			return 'nothing'

def get_part_of_picture(image_path, x_range, y_range):
	pic = np.array(misc.imread(image_path))
	# cut off the top and bottom parts of the frame which show the address bar and the dock
	# cut off the right part of the frame which may be showing the note taking menu (not important for the moment)
	pic = pic[y_range[0]:y_range[1], x_range[0]:x_range[1], :]
	return pic

def is_form(pic):
	# only the forms had any purple in them
	# however some may have purple which is off by an rgb value so we take this into effect
	# forms should have about 10000 of these pixels at the top
	if image_has_color(pic, 10000, rgb=[237, 230, 246], epsilon=0):
		return True
	# sometimes the form side goes white while loading the next question
	pic_left = pic[100:600, :600, :]
	if not image_has_color(pic_left, rgb=[255, 255, 255]) > .99:
		return False
	# the other side should have text
	# we have already estabilshed that the left side is only white pixels, so 
	# any non-white pixels on the right side tells us we're looking at a page that isn't all white
	# thus this must be part of the form
	pic_right = pic[100:600, 700:, :]
	percent_white_on_right_side = image_has_color(pic_right, rgb=[255, 255, 255])
	return percent_white_on_right_side < .98

# this is used for the ffmpeg commands and filenames
# it ads a 0 before the digit of numbers less than 10
def num_to_str(num):
	if num < 10:
		return '0'+str(num)
	return str(num)

# this is used to identify which part of the webpage a frame belongs to
# In our studies, the google form pages all had a puruple header which was not present in other pages
def image_has_color(pic, threashold=None, rgb=[237, 230, 246], upper_threashold=None, epsilon=0):
	difference_from_color = abs(pic[:,:,0] - rgb[0]) + abs(pic[:,:,1] - rgb[1]) + abs(pic[:,:,2] - rgb[2])
	num_pixels = sum(sum(difference_from_color <= epsilon))
	# if no threashold is given return the percentage of pixels that had the specified color
	if threashold is None:
		height, width, depth = pic.shape
		return float(num_pixels)/(height*width)
	# otherwise return a binary value based on the threasholds
	if upper_threashold is None:
		return num_pixels > threashold
	else:
		return (num_pixels > threashold) and (num_pixels < upper_threashold)

# a function to build each session from scratch
def build_session(sess_name):
	sess = Session(sess_name)
	sess.break_into_chunks()
	sess.find_transitions()
	sess.calculate_metadata(save_to_file=True)
	sess.find_digital_reading_transitions()

def get_session_names():
	all_sessions = []
	for foldername in settings.raw_dirs:
		if not foldername.endswith(os.sep):
			foldername += os.sep
		for filename in os.listdir(foldername+'Screen_Recordings'):
			if filename.find('_Website') == -1:
				continue
			sess_name = filename[len('Scene_'):filename.find('_Website')]
			all_sessions.append(sess_name)
	return all_sessions

def already_made_session(sess_name):
	if os.path.isdir(settings.data_dir + sess_name):
		return True
	return False

def time_action(action, message=''):
	t0 = time.time()
	output = action()
	t1 = time.time()
	print(message, t1 - t0)
	return output

if __name__ == '__main__':
	# some session ids from the pilot data
	#all_sessions = get_session_names()
	all_sessions = ['video6']

	for sess_name in all_sessions:
		#if already_made_session(sess_name):
		#	continue
		print(sess_name)
		sess = time_action(lambda: Session(sess_name), 'time to build session')
		time_action(lambda: sess.break_into_chunks(), 'time to break into 10 sec chunks')
		time_action(lambda: sess.find_transitions(), 'time to find transitions')
		time_action(lambda: sess.calculate_metadata(save_to_file=True), 'time to calculate metadata')
		time_action(lambda: sess.find_reading_transitions(part = 'typing'), 'time to find digital reading transitions')

