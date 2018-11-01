# to fix the tk error
import matplotlib
matplotlib.use('Agg')
# to access the files of a session
from video_to_frames import Session, time_to_filename, get_part_of_picture, get_session_names
# to get the list of documents
from ocr_cleanup import get_documents
# to get relevant settings
import settings
# to build a list of line occurances
from collections import defaultdict
# to take medians
import numpy as np
# to build paths (os.sep)
import os
# to read in images
from scipy import misc
# to save the scrolls
import pandas as pd
# to plot visuals
from matplotlib import pyplot as plt
# to save static line mapping
import json

# get the lines in order
def get_lines(example_doc):
	correct_doc_filepath = settings.correct_text_dir + os.sep + example_doc.attrs['filename']
	with open(correct_doc_filepath, 'r') as infile:
		return [line.strip() for line in infile if len(line.strip()) > 0]

# is the previous line correct for the given line
def keys_math(current_key, prev_key, lines_in_order):
	if prev_key is None:
		return current_key == lines_in_order[0]
	else:
		index = lines_in_order.index(current_key)
		return lines_in_order[index-1] == prev_key

# a helper function to build each line
def build_line_info(line_list, line_key, prev_height=None, prev_top=0):
	tops = []
	bottoms = []
	get_top = lambda l : l.title['bbox'].top
	get_bottom = lambda l : l.title['bbox'].bottom
	for line, prev_line in line_list:
		if prev_height is None:
			tops.append(get_top(line))
			bottoms.append(get_bottom(line))
		else:
			p_top = get_top(prev_line)
			p_bottom = get_bottom(prev_line)
			p_height = p_bottom - p_top
			current_top = get_top(line)
			current_bottom = get_bottom(line)
			# get the distance to the previous line scaled by the
			# p_height/prev_height
			distance_from_top_to_prev_top = (current_top - p_top) * (p_height/prev_height)
			distance_from_bottom_to_prev_top = (current_bottom - p_top) * (p_height/prev_height)
			tops.append(distance_from_top_to_prev_top + prev_top)
			bottoms.append(distance_from_bottom_to_prev_top + prev_top)
	return (line_key, np.mean(tops), np.mean(bottoms))

# stitch together a single representation of the article
# returns a list of tuples that are (line_text, line_top, line_bottom)
def stitch_lines(sess, part='digital reading', save=True, redo=False):
	# if already calculated, load (as long as not redoing)
	if not redo and os.path.isfile(sess.dir_name + os.sep + settings.stitched_together_json_file):
		with open(sess.dir_name + os.sep + settings.stitched_together_json_file, 'r') as fp:
			return json.load(fp)
	lines_dict = defaultdict(list)
	# for each line put the pair of the line and the previous line in the lines_dict
	documents = get_documents(sess, redo=True, alt_dir_name=None, part=part, source_dir_name=settings.xml_dir)
	if len(documents) == 0:
		return []
	lines_in_order = get_lines(documents[0])
	for doc in documents:
		prev_line = None
		prev_key = None
		for line in doc.lines:
			line_key = line.attrs['updated_line']
			if line_key == '':
				continue
			if keys_math(line_key, prev_key, lines_in_order):
				lines_dict[line_key].append((line, prev_line))
			prev_line = line
			prev_key = line_key
	# go through the lines and build a list of line positions as output
	output = []
	prev_line_key = None
	prev_height = None
	prev_top = 0
	for next_line_key in lines_in_order:
		next_line = build_line_info(lines_dict[next_line_key], next_line_key, prev_height, prev_top)
		output.append(next_line)
		prev_line_key = next_line_key
		prev_height = next_line[2] - next_line[1]
		prev_top = next_line[1]
	# save so we don't need to calculate this again
	if save:
		with open(sess.dir_name + os.sep + settings.stitched_together_json_file, 'w') as fp:
			json.dump(output, fp)
	return output

# get the two values that describe a mapping function
def get_possible_map_values(first_line, last_line, static_line_dict):
	# set the frame points
	top_frame_point = first_line.title['bbox'].top
	bottom_frame_point = last_line.title['bbox'].bottom
	# set the static points
	top_static_point = static_line_dict[first_line.attrs['updated_line']][0]
	bottom_static_point = static_line_dict[last_line.attrs['updated_line']][1]
	# calculate multipiler
	multipiler = (bottom_static_point-top_static_point)/(bottom_frame_point-top_frame_point)
	# calculate adder
	adder = top_static_point - (top_frame_point * multipiler)
	# return the three values needed to build the map
	return multipiler, adder

# this function produces a function which maps a vertical point in a frame image to
# a point on the image of the correct document which is made by stiching the ocr results together
def get_mapping_function(sess, frame_document, static_list_of_lines, include_low_confidence=False, debug_mode=False):
	doc_lines = [l for l in frame_document.lines if l.attrs['updated_line'] != '']
	if not include_low_confidence:
		doc_lines = doc_lines[1:-1]
	static_line_dict = dict([(line_text, (top, bottom)) for line_text, top, bottom in static_list_of_lines])
	# don't count documents without sufficient lines
	if len(doc_lines) <= 1:
		return lambda x: None
	multipilers = []
	adders = []
	rows = []
	# look at a bunch of line pairs
	for first_line_index in range(0, (len(doc_lines)-1)):
		first_line = doc_lines[first_line_index]
		for last_line_index in range((first_line_index + 1), len(doc_lines)):
			last_line = doc_lines[last_line_index]
			m, a = get_possible_map_values(first_line, last_line, static_line_dict)
			multipilers.append(m)
			adders.append(a)
			rows.append([first_line.attrs['updated_line'], last_line.attrs['updated_line'], m, a])
	# save for debugging
	if debug_mode:
		df = pd.DataFrame(rows, columns=['first', 'last', 'multiplier', 'adder'])
		if not os.path.isdir(sess.dir_name + os.sep + settings.mapping_dir):
			os.mkdir(sess.dir_name + os.sep + settings.mapping_dir)
		df.to_csv(sess.dir_name + os.sep + settings.mapping_dir + os.sep + time_to_filename(frame_document.time, extension='csv'), index=False)
	# final values
	final_m = np.median(multipilers)
	final_a = np.median(adders)
	return lambda x: (x * final_m) + final_a

# calculate scrolling for a session
def calculate_scrolling(sess, part='digital reading', redo=False, save=True, include_low_confidence=False):
	# load if already calculated
	if redo is False:
		filepath = sess.dir_name + os.sep + settings.scrolling_csv_file
		if os.path.isfile(filepath):
			return pd.read_csv(filepath)
	# get the lines as a single list
	static_line_list = stitch_lines(sess, part=part)
	# get the list of documents
	documents = get_documents(sess, redo=True, alt_dir_name=None, part=part, source_dir_name=settings.xml_dir)
	# store all the output as rows of time, top_of_frame, bottom_of_frame
	top_value = None
	bottom_value = None
	rows = []
	# retrieve the time and top of page values for each document
	for doc in documents:
		t = doc.time
		# get dimensions of an example frame
		if top_value is None:
			frame_filepath = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + time_to_filename(t)
			img = np.array(misc.imread(frame_filepath))
			# not unscalling properly right now
			bottom_value = img.shape[0] * 2
			top_value = 0
		mapping_function = get_mapping_function(sess, doc, static_line_list, include_low_confidence=include_low_confidence)
		y_top = mapping_function(top_value)
		y_bottom = mapping_function(bottom_value)
		# filter out unlikely scrolls (those with less than 4 lines recognized)
		# these times will be replaced with the times before them
		# (they are most likely to be times when the document is outside the corpus or the screen is very zoomed)
		if y_top is None:
			continue
		rows.append((t, y_top, y_bottom))
	df = pd.DataFrame(rows, columns=['Time', 'Top', 'Bottom'])
	if save:
		df.to_csv(sess.dir_name + os.sep + settings.scrolling_csv_file, index=False)
	return df

# calculate scrolling for all sessions
def save_scrolling_for_all_sessions(part='digital reading'):
	for sess_name in get_session_names():
		sess = Session(sess_name)
		calculate_scrolling(sess, part=part, redo=True)

# visualize scrolling from a session
def visualize_scrolling(sess, part='digital reading', picture_directory = None, include_labels=True):
	# get the scrolling data
	data = list(calculate_scrolling(sess, part=part).apply(lambda x: (x['Time'], x['Top'], x['Bottom']), axis=1))
	if len(data) == 0:
		return
	# expand the data to cover the full time period for each frame
	data += [(data[i][0]-.05, data[i-1][1], data[i-1][2]) for i in range(1,len(data))]
	data.sort()
	x_vals, y_top_vals, y_bottom_vals = zip(*data)
	# for scaling

	# older idea: scale according to static lines
	# problem: this list is scaled arbitrarily by whatever scale the first line is chosen to be
	# static_lines = stitch_lines(sess, part=part)
	# final_line_difference = static_lines[-1][2] - static_lines[-2][2]

	# currently this is just the maximum value measured
	# would like to fix so the viz still works if the user didn't scroll to the bottom
	max_height = max(y_bottom_vals)
	# if there is a picture, load it and scale the image values
	if picture_directory is not None:
		# get the picture name
		documents = get_documents(sess, redo=True, alt_dir_name=None, part=part, source_dir_name=settings.xml_dir)
		picture_directory = picture_directory if picture_directory.endswith(os.sep) else picture_directory + os.sep
		image_path = picture_directory + documents[0].attrs['filename'][:-len('.txt')] + '.png'
		img = np.array(misc.imread(image_path))
		height, width, _ = img.shape
		plt.imshow(img)
		# scale the plot to fit over the image
		plt.xlim([0, width])
		max_width = width
		plt.ylim([height, 0])
		# save instructions for unscaling
		unscale_x = lambda x: (x/width*(max(x_vals)-min(x_vals)))+min(x_vals)
		# scale values
		x_scaled_vals = [(x-min(x_vals))/(max(x_vals)-min(x_vals))*width for x in x_vals]
		y_scaled_top_vals = [y/max_height*height for y in y_top_vals]
		y_scaled_bottom_vals = [y/max_height*height for y in y_bottom_vals]
		# plot data on top
		plt.fill_between(x_scaled_vals, y_scaled_top_vals, y_scaled_bottom_vals, alpha=.2)
	else:
		unscale_x = lambda x: x
		# scale the plot to fit over the image
		plt.xlim([0, max(x_vals)])
		max_width = max(x_vals)
		plt.ylim([max_height, 0])
		# plot data on top
		plt.fill_between(x_vals, y_top_vals, y_bottom_vals, alpha=.2)
	if include_labels:
		plt.xlabel('Time Since Session Started')
		plt.ylabel('Vertical Position of Screen')
	# fix x ticks
	x_tick_vals = [x for x in plt.xticks()[0] if x <= max_width]
	x_tick_vals_unscaled = [unscale_x(x) for x in x_tick_vals]
	num_to_str = lambda num: str(int(num)) if num >= 10 else '0'+str(int(num))
	to_time_str = lambda t: num_to_str(int(t/60)) + ':' + num_to_str(t-(int(t/60)*60))
	plt.xticks(x_tick_vals, [to_time_str(xt) for xt in x_tick_vals_unscaled])
	# get rid of y ticks
	plt.yticks([], [])
	plt.savefig(sess.dir_name + os.sep + settings.scrolling_viz_file, dpi=800)
	# make sure there is nothing still in the figure
	plt.clf()

if __name__ == '__main__':
	#save_scrolling_for_all_sessions()
	for sess_name in get_session_names():
		sess = Session(sess_name)
		# rows = stitch_lines(sess, redo=True)
		# df = pd.DataFrame(rows, columns=['Line Text', 'Top', 'Bottom'])
		# df.to_csv(sess.dir_name + os.sep + 'stitched.csv', index=False)
		visualize_scrolling(sess, part='digital reading', picture_directory = 'parts_for_viz/synthasized')


