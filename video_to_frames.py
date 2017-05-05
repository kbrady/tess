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
		self.webcam_filename = self.calculate_filenames('Webcam')
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
		for path_start in [settings.raw_dir_a, settings.raw_dir_b]:
			path = path_start + dir_name
			path = path if path.endswith(os.sep) else path + os.sep
			for filename in os.listdir(path):
				filename_part = filename[filename.find('_')+1:]
				if filename_part.startswith(self.id):
					# it is posible that one participants id is a substring of another's so we need to check this
					filename_part = filename_part[len(self.id):]
					if filename_part.startswith('_Website') or filename_part.startswith('.txt'):
						output.append(path + filename)
		# exactly one file for each type should be found for each session
		if len(output) != 1:
			raise Exception(str(len(output))+' files found for '+self.id+': '+','.join(output))
		return output[0]
	
	# a handy function to see if we got all the raw data right
	def __repr__(self):
		output = str(self.name_string) + '\n' 
		output += str(self.screen_recordings) + '\n'
		output += str(self.sensor_data) + '\n'
		output += str(self.webcam)
		return output

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
		filename = time_to_filename(current_time)
		# in order to run this you'll need ffmpeg installed. I haven't found a good frame puller in python
		command = 'ffmpeg -ss 00:'
		# calculate the minutes and seconds of the time
		minutes = int(current_time/60)
		seconds = current_time - (minutes * 60)
		command += num_to_str(minutes)+':'+num_to_str(seconds)
		command += ' -i '+self.screen_recording_filename+' -frames:v 1 '+dir_name+os.sep+filename
		command = command.replace('(','\(')
		command = command.replace(')','\)')
		os.system(command)

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
			with open(self.dir_name + os.sep + settings.metadata_file, 'w') as metadata_output:
				metadata_output.write(json.dumps(metadata, ensure_ascii=False))
		# return the calculated metadata
		return metadata

	def find_transitions(self):
		assignments = self.assess_stimuli_timestamps()
		times = assignments.keys()
		times = [(filename_to_time(t), t) for t in times]
		times.sort()
		# go through the existing frames in order to find transitions
		for i in range(len(times)-1):
			# do a binary search for every gap that is more than .1 seconds wide
			if assignments[times[i][1]] != assignments[times[i+1][1]]:
				if times[i+1][0] - times[i][0] <= .1:
					continue
				self.binary_frame_search(times[i][0], times[i+1][0], assignments[times[i][1]], assignments[times[i+1][1]])

	def binary_frame_search(self, start_time, end_time, start_value, end_value, key=lambda x, y: x == y):
		if start_time > end_time or end_time - start_time <= .15:
			return
		if key(start_value, end_value):
			return
		middle_time = float(int((float(start_time + end_time)/2)*10))/10
		# might not actually get a middle time due to round off error
		if middle_time == start_time or middle_time == end_time:
			return
		#print (time_to_filename(start_time), time_to_filename(middle_time), time_to_filename(end_time))
		middle_filename = time_to_filename(middle_time)
		self.screen_time_to_picture(middle_time)
		middle_value = self.assess_stimuli_timestamps(file_list=[middle_filename])[middle_filename]
		self.binary_frame_search(start_time, middle_time, start_value, middle_value, key=key)
		self.binary_frame_search(middle_time, end_time, middle_value, end_value, key=key)

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

def is_form(pic):
	# only the forms had any purple in them so even a small amount of purple means it's a form
	if image_has_color(pic, 10, rgb=[237, 230, 246]):
		return True
	# sometimes the form side goes white while loading the next question
	pic_left = pic_left = pic[100:600, :600, :]
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
def image_has_color(pic, threashold=None, rgb=[237, 230, 246], upper_threashold=None):
	num_pixels = sum(sum((pic[:,:,0] == rgb[0]) & (pic[:,:,1] == rgb[1]) & (pic[:,:,2] == rgb[2])))
	# if no threashold is given return the percentage of pixels that had the specified color
	if threashold is None:
		height, width, depth = pic.shape
		return float(num_pixels)/(height*width)
	# otherwise return a binary value based on the threasholds
	if upper_threashold is None:
		return num_pixels > threashold
	else:
		return (num_pixels > threashold) and (num_pixels < upper_threashold)

if __name__ == '__main__':
	# some session ids from the pilot data
	pilot_sessions = ['seventh_participant', 'fifth_participant', 'third_student_participant', 'first_student_participant_second_take', 'first_student_participant', 'Amanda', 'eighth_participant', 'sixth_participant', 'fourth-participant-second-version' , 'fourth_participant', 'second_student_participant']

	# At some point I need to deal with what happens when there are spaces in the participant name
	#, 'Kate is testing']

	for sess_name in pilot_sessions:
		sess = Session(sess_name)
		sess.calculate_metadata(True)

	# image_path = '/Users/kate/Documents/research/pipeline-data/seventh_participant/frame-images/16-40.jpg'
	# pic = np.array(misc.imread(image_path))
	# # cut off the top and bottom parts of the frame which show the address bar and the dock
	# # cut off the right part of the frame which may be showing the note taking menu (not important for the moment)
	# pic = pic[50:800, :900, :]
	# print image_has_color(pic, rgb=[255, 255, 255])

