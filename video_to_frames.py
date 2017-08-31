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

class Session:
	def __init__(self, id_string):
		# this is the string by which this participant will be recognized by from now on
		self.id = id_string
		# make a data folder to put things in
		self.dir_name = settings.data_dir+self.id
		if not os.path.isdir(self.dir_name):
			os.mkdir(self.dir_name)
		# find the files among the raw data that were recorded for this session
		self.screen_recording_filename = self.calculate_filenames('Screen_Recordings')
		self.sensor_data_filename = self.calculate_filenames('Sensor_Data')
		# load any metadata that exists
		self.metadata = []
		if os.path.exists(self.dir_name + os.sep + settings.metadata_file):
			with open(self.dir_name + os.sep + settings.metadata_file, 'r') as metadata_input:
				json_str = ' '.join([line for line in metadata_input])
				# sometimes the program gets interupted before a dump is complete
				if len(json_str) > 5:
					self.metadata = json.loads(json_str)
	
	def calculate_filenames(self, dir_name):
		output = []
		# look through the files in both conditions, this makes it easier than remember all the condition pairings
		for path_start in settings.raw_dirs:
			path = path_start + dir_name
			path = path if path.endswith(os.sep) else path + os.sep
			for filename in os.listdir(path):
				filename_part = filename[filename.find('_')+1:]
				if filename_part.startswith(self.id):
					# it is posible that one participants id is a substring of another's so we need to check this
					filename_part = filename_part[len(self.id):]
					if filename_part.startswith('_Website') or filename_part.startswith('.txt'):
						output.append(path + filename)
		# there are multiple dump files because iMotions is stupid
		if len(output) == 2:
			parts_1 = ouput[0].split('Dump')
			parts_2 = ouput[1].split('Dump')
			if parts_1[0] == parts_2[0] and parts_1[1][3:] == parts_2[1][3:]:
				with open(output[0], 'r') as infile:
					for line in infile:
						if line.startswith('#Date : '):
							date_1 = int(line[len('#Date : '):len('#Date : ')+8])
							break
				with open(output[1], 'r') as infile:
					for line in infile:
						if line.startswith('#Date : '):
							date_2 = int(line[len('#Date : '):len('#Date : ')+8])
							break
				if date_1 > date_2:
					os.remove(output[1])
					output = [output[0]]
				else:
					os.remove(output[0])
					output = [output[1]]
		# exactly one file for each type should be found for each session
		if len(output) != 1:
			raise Exception(str(len(output))+' files found for '+self.id+': '+','.join(output))
		return output[0]
	
	# a handy function to see if we got all the raw data right
	def __repr__(self):
		output = str(self.name_string) + '\n' 
		output += str(self.screen_recordings) + '\n'
		output += str(self.sensor_data)
		return output

	# switch only_if_frame_does_not_exist back to True
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
		dir_name = self.dir_name + os.sep + 'frame-images'
		if not os.path.isdir(dir_name):
			os.mkdir(dir_name)
		# only replace spaces in dir_name with backslash spaces after running os commands on the original name
		# (such as building the directory in the first place)
		#dir_name = dir_name.replace(' ', '\ ')
		#screen_recording_filename = self.screen_recording_filename.replace(' ', '\ ')
		filename = time_to_filename(current_time)
		# in order to run this you'll need ffmpeg installed. I haven't found a good frame puller in python
		# nohup stops the process from ending when the python script does
		# [https://stackoverflow.com/questions/1605520/how-to-launch-and-run-external-script-in-background#1605539]
		command = ['ffmpeg', '-ss']
		# calculate the minutes and seconds of the time
		minutes = int(current_time/60)
		seconds = current_time - (minutes * 60)
		command.append('00:'+num_to_str(minutes)+':'+num_to_str(seconds))
		command += ['-i', self.screen_recording_filename, '-frames:v', '1', dir_name+os.sep+filename]
		#escape_fun = lambda part : part.replace('(','\(').replace(')','\)').replace(' ', '\ ')
		#shell_command = ' '.join([escape_fun(x) for x in command]) + ' &'
		#command = command.replace('(','\(')
		#command = command.replace(')','\)')
		# Apparently Popen stops the python script after running
		subprocess.call(command)
		#sys.exit()

	# a function to save time by not running ffmpeg more than necessary
	def picture_for_frame_exists(self, current_time):
		# if the directory doesn't exist, neither does any file in it
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		if not os.path.isdir(dir_name):
			return False
		filename = time_to_filename(current_time)
		return os.path.exists(dir_name + os.sep + filename)
	
	def break_into_10_second_chunks(self):
		duration = imageio.get_reader(self.screen_recording_filename, 'ffmpeg').get_meta_data()['duration']
		current_time = 0
		# pull out frames for every 10 seconds until the end of the video
		while current_time < duration:
			self.screen_time_to_picture(current_time)
			current_time += 10

	def assess_stimuli_timestamps(self, file_list=None):
		assignments = {}
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		if file_list is None:
			file_list = os.listdir(dir_name)
		for image_file in file_list:
			part_of_stimuli = figure_out_part_of_stimuli_frame_is_in(dir_name + os.sep + image_file)
			assignments[image_file] = part_of_stimuli
		return assignments

	# the reading is the same if the pixels for the first line are the same and the sidebar is in the same position
	def find_digital_reading_transitions(self):
		if len(self.metadata) == 0:
			self.metadata = self.calculate_metadata(save_to_file=True)
		digital_reading_times = [x for x in self.metadata if x['part'] == 'digital reading']
		dir_name = self.dir_name + os.sep + settings.frame_images_dir
		picture_value = lambda filename: get_part_of_picture(dir_name + os.sep + filename, x_range=[0, 1400], y_range=[600,700])
		for reading_interval in digital_reading_times:
			filenames = self.get_image_filenames_in_timespan(reading_interval['start_time'], reading_interval['end_time'])
			for i in range(len(filenames)-1):
				start_value = picture_value(filenames[i])
				end_value = picture_value(filenames[i+1])
				if not (start_value == end_value).all():
					start_time = filename_to_time(filenames[i])
					end_time = filename_to_time(filenames[i+1])
					if end_time - start_time > .1:
						self.binary_frame_search(start_time, end_time, start_value, end_value, value_fun=picture_value)
			# now that we have made sure we have all the necessary files, look for the transitions
			filenames = self.get_image_filenames_in_timespan(reading_interval['start_time'], reading_interval['end_time'])
			transition_list = [filename_to_time(filenames[0])]
			for i in range(len(filenames)-1):
				start_value = picture_value(filenames[i])
				end_value = picture_value(filenames[i+1])
				if not (start_value == end_value).all():
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

	def binary_frame_search(self, start_time, end_time, start_value, end_value, value_fun):
		if start_time > end_time or end_time - start_time <= .15:
			return
		# in some cases we compare whether the catagories of images
		# (figured out by the functions below) are the same
		# in other cases we want to check if the matracies representing the
		# images are the same
		if type(start_value) == str:
			key = lambda x, y: x == y
		else:
			key = lambda x, y: (x == y).all()
		if key(start_value, end_value):
			return
		middle_time = float(int((float(start_time + end_time)/2)*10))/10
		# might not actually get a middle time due to round off error
		if middle_time == start_time or middle_time == end_time:
			return
		#print (time_to_filename(start_time), time_to_filename(middle_time), time_to_filename(end_time))
		middle_filename = time_to_filename(middle_time)
		self.screen_time_to_picture(middle_time)
		middle_value = value_fun(middle_filename)
		self.binary_frame_search(start_time, middle_time, start_value, middle_value, value_fun=value_fun)
		self.binary_frame_search(middle_time, end_time, middle_value, end_value, value_fun=value_fun)

def time_to_filename(current_time):
	# calculate the minutes and seconds of the time and use these values to create the filename
	minutes = int(current_time/60)
	seconds = current_time - (minutes * 60)
	filename = num_to_str(minutes)+'-'+num_to_str(seconds)+'.jpg'
	return filename

def filename_to_time(filename):
	parts = filename.split('.')
	minutes, seconds = [int(x) for x in parts[0].split('-')]
	if len(parts) > 2:
		miliseconds = float('.'+parts[1])
	else:
		miliseconds = 0
	return minutes * 60 + seconds + miliseconds

def figure_out_part_of_stimuli_frame_is_in(image_path):
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
	sess.break_into_10_second_chunks()
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

if __name__ == '__main__':
	# some session ids from the pilot data
	all_sessions = get_session_names()
	print all_sessions

	t0 = time.time()
	for sess_name in all_sessions:
		if already_made_session(sess_name):
			continue
		print sess_name
		sess = Session(sess_name)
		sess.break_into_10_second_chunks()
		sess.find_transitions()
		sess.calculate_metadata(save_to_file=True)
		sess.find_digital_reading_transitions()
	t1 = time.time()
	print 'time taken', t1 - t0

