# to read in the screen grab
import numpy as np
from scipy import misc
# to read the length of the video
import imageio
# to find files and run ffmpeg
import os
# to look in the right places
import settings

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
		# calculate the minutes and seconds of the time and use these values to create the filename
		minutes = int(current_time/60)
		seconds = current_time - (minutes * 60)
		filename = num_to_str(minutes)+'-'+num_to_str(seconds)+'.jpg'
		# in order to run this you'll need ffmpeg installed. I haven't found a good frame puller in python
		command = 'ffmpeg -ss 00:'
		command += num_to_str(minutes)+':'+num_to_str(seconds)
		command += ' -i '+self.screen_recording_filename+' -frames:v 1 '+dir_name+os.sep+filename
		command = command.replace('(','\(')
		command = command.replace(')','\)')
		os.system(command)

	# a function to save time by not running ffmpeg more than necessary
	def picture_for_frame_exists(self, current_time):
		# if the directory doesn't exist, neither does any file in it
		dir_name = self.dir_name + os.sep + 'frame-images'
		if not os.path.isdir(dir_name):
			return False
		# calculate the filename
		minutes = int(current_time/60)
		seconds = current_time - (minutes * 60)
		filename = num_to_str(minutes)+'-'+num_to_str(seconds)+'.jpg'
		return os.path.exists(dir_name + os.sep + filename)
	
	def break_into_10_second_chunks(self):
		duration = imageio.get_reader(self.screen_recording_filename, 'ffmpeg').get_meta_data()['duration']
		current_time = 0
		# pull out frames for every 10 seconds until the end of the video
		while current_time < duration:
			self.screen_time_to_picture(current_time)
			current_time += 10

# this is used for the ffmpeg commands and filenames
# it ads a 0 before the digit of numbers less than 10
def num_to_str(num):
	if num < 10:
		return '0'+str(num)
	return str(num)

if __name__ == '__main__':
	# some session ids from the pilot data
	pilot_sessions = ['seventh_participant', 'fifth_participant', 'third_student_participant', 'first_student_participant_second_take', 'first_student_participant', 'Amanda', 'eighth_participant', 'sixth_participant', 'fourth-participant-second-version' , 'fourth_participant', 'second_student_participant', 'Kate is testing']

	for sess_name in pilot_sessions:
		sess = Session(sess_name)
		sess.break_into_10_second_chunks()