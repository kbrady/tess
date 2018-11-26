# to access correct directories
import settings
# to make visualizations
from find_highlights import make_highlight_viz, get_highlight_visualization_matrix
from find_scrolls import visualize_scrolling
# to reason about sessions
from video_to_frames import Session, get_session_names, time_to_filename, filename_to_time
# to access files
import os
# to make plots
from matplotlib import pyplot as plt
# to load frame images
from PIL import Image
# to run ffmpeg in the background
import subprocess

def make_explanation_frame(sess, time, frame_filename, series_filename, min_time, max_time, part='digital reading'):
    # make one figure with all three images
    plt.subplot(221)
    visualize_scrolling(sess, part=part, picture_directory = settings.stitched_img_directory, include_labels=False, save_and_clear=False)
    # add the line for the time
    min_x, max_x = plt.xlim()
    plt.axvline(x = (time-min_time)/(max_time-min_time)*max_x, color='r')

    # highlight visual
    plt.subplot(222)
    make_highlight_viz(sess, words_per_label=3, part=part, save_and_clear=False, include_labels=False)
    # add the line for the time
    min_x, max_x = plt.xlim()
    plt.plot([min_x, max_x], [int(time/settings.little_t), int(time/settings.little_t)], 'r')

    # add frame from screen recording
    plt.subplot(212)
    img = Image.open(sess.dir_name + os.sep + settings.frame_images_dir + os.sep + frame_filename)
    plt.imshow(img)
    plt.xticks([])
    plt.yticks([])
    if not os.path.isdir(sess.dir_name + os.sep + settings.viz_explanation_frames):
    	os.mkdir(sess.dir_name + os.sep + settings.viz_explanation_frames)
    plt.savefig(sess.dir_name + os.sep + settings.viz_explanation_frames + os.sep + series_filename, dpi=800)
    plt.clf()

def make_explanation_frames_for_session(sess, part='digital reading'):
	# get the largest reading time
	# (in the future it might be good to make multiple visualizations)
	reading_times = max([x for x in sess.metadata if x['part'] == part], key=lambda x: max(x['transitions']) - min(x['transitions']))
	reading_times = reading_times['transitions']

	if len(reading_times) == 0:
		return

	reading_times.sort()
	all_times = list(range(int(reading_times[0]/settings.little_t), int(reading_times[-1]/settings.little_t)))
	length_of_indexes = len(str(len(all_times)))

	# get all the frame times that frames exist for not just reading times (this will make the video less choppy)
	frame_times = [filename_to_time(f) for f in os.listdir(sess.dir_name + os.sep + settings.frame_images_dir) if not f.startswith('.')]
	frame_times.sort()
	
	# set the max and min times to scale the time appropriately for the scrolling visual
	min_time = reading_times[0]
	max_time = reading_times[-1]

	# a function to turn a time into an index
	def index_to_filename(index):
		output = str(index)
		while len(output) < length_of_indexes:
			output = '0' + output
		return output + '.png'

	# the indexes for the two types of frames
	explanatory_frame_index = 0
	frame_times_index = 0

	# go through the times and make frames for the explanation video
	for time_div_little_t in all_times:
		# set the time
		time = time_div_little_t * settings.little_t

		# increment the index to the frames if applicable
		if (frame_times_index + 1) < len(frame_times) and frame_times[frame_times_index+1] <= time:
			frame_times_index += 1

		# set the filenames for the explanatory frame and the screen shot frame
		series_filename = index_to_filename(explanatory_frame_index)
		frame_filename = time_to_filename(frame_times[frame_times_index])

		# make the explanatory frame
		make_explanation_frame(sess, time, frame_filename, series_filename, min_time, max_time, part=part)

		# increment the explanatory frame index
		explanatory_frame_index += 1

def make_explanation_video(sess):

	# set the directory where frames are stored
	dir_name = sess.dir_name + os.sep + settings.viz_explanation_frames + os.sep
	length_of_zeros = None

	# get a sample frame to observe how long the filename is
	for filename in os.listdir(dir_name):
		if filename.startswith('.'):
			continue
		length_of_zeros = len(filename[:filename.find('.')])
		break

	# if there is nothing in the frames directory, exit
	if length_of_zeros is None:
		return

	# set the matching string
	frame_matching_string = dir_name + '%0' + str(length_of_zeros) + 'd.png'
	command = ['ffmpeg', '-r', str(1/settings.little_t), '-i', frame_matching_string, '-vcodec', 'mpeg4', '-y', sess.dir_name + os.sep + settings.explanation_video]

	# build the video
	subprocess.call(command)

if __name__ == '__main__':
	session_names = get_session_names()
	# only make an explanation for the first session
	# be aware this takes a VERY long time per video
	for sess_name in session_names[:1]:
		sess = Session(sess_name)
		# make a visualization
		make_explanation_frames_for_session(sess)
		make_explanation_video(sess)