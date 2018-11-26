# to fix matplotlib errors
import matplotlib
matplotlib.use('Agg')
# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename, filename_to_time
# get each document
from ocr_cleanup import get_documents
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save output from some functions
import csv
# to build documents
from Document import Document
# to build hash table for document discovery
from collections import defaultdict, Counter
# to visualize stuff
from matplotlib import pyplot as plt
from matplotlib import image as mpimg
# to save found highlights
import json
# if thresholding is bad
from sklearn.cluster import KMeans
# to save numpy arrays as images
from PIL import Image

# convert image to grayscale (weight RGB acording to human eye)
def rgb2gray(rgb):
	return np.dot(rgb[...,:3], [0.299, 0.587, 0.114])

# get the median color among a set of selected pixels by taking the median of each color band
def get_median_color(img, boolean_array):
	red = img[:,:,0]
	red = np.median(red[boolean_array].flatten())
	green = img[:,:,1]
	green = np.median(green[boolean_array].flatten())
	blue = img[:,:,2]
	blue = np.median(blue[boolean_array].flatten())
	return (red, green, blue)

#functions for seperating an image

# I use 150 instead of 128 as the threshold since light colors
# are more distinguishable (and thus used in text more often) than dark colors
def threshold_img(img, threshold=150):
	flat_image = rgb2gray(img)
	return (flat_image > threshold)

# this method uses clustering instead of thresholding
# it takes longer since KMeans is sequential, but it can seperate images when both
# the background and text are above or below a threshold
def cluster_img(img):
	kmeans = KMeans(n_clusters=2, random_state=0).fit(img.reshape(-1,img.shape[2]))
	labels = np.array(kmeans.labels_)
	h, w, _ = img.shape
	return labels.reshape((h, w)) == 0

# seperate an image into light and dark colors and take the median of each color set
def seperate_image(img, method=cluster_img):
	flat_image = rgb2gray(img)
	# get the boolean array that seperates text from the background
	light = method(img)
	# get the percentage of the picture that is light
	light_total = sum(sum(light))
	light_perc = light_total/flat_image.size
	# return background, then foreground
	if light_perc > .5:
		return get_median_color(img, light), get_median_color(img, ~light), light_perc
	return get_median_color(img, ~light), get_median_color(img, light), 1-light_perc

# find the difference between two RGB values
def find_color_difference(input_color, comp_color):
	return np.sqrt(sum([(input_color[i] - comp_color[i]) ** 2 for i in range(3)]))

# find the closest color pair in the local_settings highlight_color_pairs list to
# the median colors detected in an image
def find_closest_color(background_col, foreground_col, no_bolding = False):
	closest_diff = None
	closest_color = None
	for col_name in settings.highlight_color_pairs:
		background_comp, foreground_comp = settings.highlight_color_pairs[col_name]
		diff = find_color_difference(background_col, background_comp) + find_color_difference(foreground_col, foreground_comp)
		# if bolding is possible we must consider that the colors may be reversed
		swap = False
		if not no_bolding:
			diff_2 = find_color_difference(background_col, foreground_comp) + find_color_difference(foreground_col, background_comp)
			if diff_2 < diff:
				diff = diff_2
				swap = True
		if closest_diff is None or diff < closest_diff:
			closest_diff = diff
			closest_color = col_name
	return closest_color, swap

# find the highlight color for a word
def find_highlight_color(word, img, no_bolding = False):
	# get segment to investigate
	right, left, top, bottom = word.title['bbox'].right, word.title['bbox'].left, word.title['bbox'].top, word.title['bbox'].bottom
	right, left, top, bottom = int(right), int(left), int(top), int(bottom)
	# add three pixels to each side to get more background pixels (for short words)
	sub_three = lambda x: max([0, x-3])
	add_three = lambda x, y: min([y, x+3])
	height, width, _ = img.shape
	# make sure we aren't violating physics
	for val in [right, left]:
		if val >= width:
			return
	for val in [top, bottom]:
		if val >= height:
			return
	img_segment = img[sub_three(top):add_three(bottom, height), sub_three(left):add_three(right, width), :]
	if (img_segment.size < 9):
		return
	# get the colors associated with this word
	background_col, foreground_col, background_perc = seperate_image(img_segment)
	# get the label for this word
	highlight_label, swap = find_closest_color(background_col, foreground_col, no_bolding = no_bolding)
	# assign the colors and label to the word
	word.attrs['background_color'] = str(foreground_col) if swap else str(background_col)
	word.attrs['foreground_color'] = str(background_col) if swap else str(foreground_col)
	word.attrs['background_color_perc'] = str(round(background_perc, 2))
	word.attrs['highlight'] = highlight_label

# find the highlight colors for a document
def find_highlights(doc, img_dir_path, no_bolding = False):
	filepath_parts = doc.input_file.split(os.sep)
	filename = filepath_parts[-1][:-len('hocr')] + 'jpg'
	img_path = img_dir_path + os.sep + filename
	img = mpimg.imread(img_path)
	for line in doc.lines:
		for word in line.children:
			find_highlight_color(word, img, no_bolding = no_bolding)
	doc.save()

# find the highlight colors for a session
def find_all_highlights(sess, part='digital reading', img_dir_path=settings.frame_images_dir, no_bolding = False, dir_to_read_from = settings.global_id_dir, dir_to_save_to = settings.highlights_dir, recalculate=False):
	# get documents
	documents = get_documents(sess, redo=recalculate, alt_dir_name=dir_to_save_to, source_dir_name=dir_to_read_from, part=part)
	# get the right path to images
	img_dir_path = sess.dir_name + os.sep + img_dir_path
	# fing highlights for each document
	for doc in documents:
		find_highlights(doc, img_dir_path, no_bolding = no_bolding)

def find_highlights_for_each_session(no_bolding=False, img_dir_path=settings.frame_images_dir, part='digital reading', dir_to_read_from = settings.global_id_dir, dir_to_save_to = settings.highlights_dir, recalculate=False):
	# get the session names
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		# avoid sessions where the corrections have not been completely calculated
		if not os.path.isfile(sess.dir_name + os.sep + 'time_to_assign_ids.json'):
			continue
		# don't recalculate
		if not recalculate and os.path.isfile(sess.dir_name + os.sep + 'time_to_find_highlights.json'):
			continue
		time_to_find_highlights = {}
		t0 = time.time()
		find_all_highlights(sess, part=part, no_bolding = no_bolding, img_dir_path=img_dir_path, dir_to_read_from = dir_to_read_from, dir_to_save_to = dir_to_save_to, recalculate=recalculate)
		time_to_find_highlights['find_all_highlights'] = time.time() - t0
		with open(sess.dir_name + os.sep + 'time_to_find_highlights.json', 'w') as fp:
			json.dump(time_to_find_highlights, fp)

# make a report of when highlights were made and editted
def make_report(sess, part='digital reading'):
	# get the documents for this session
	documents = get_documents(sess, redo=True, alt_dir_name=settings.highlights_dir, source_dir_name=settings.highlights_dir, part=part, edit_dir=settings.editor_dir)
	times_and_documents = [(filename_to_time(doc.input_file), doc) for doc in documents]
	times_and_documents.sort()
	report = defaultdict(list)
	# keep track of the current state of each word
	# assume the starting color is white
	current_state = defaultdict(lambda:'white')
	for doc_time, doc in times_and_documents:
		new_highlight_ids = {}
		words = [w for l in doc.lines for w in l.children if 'highlight' in w.attrs]
		for w in words:
			# if there is no global id, skip
			if 'global_ids' not in w.attrs:
				continue
			# treat each global id as different
			id_group = [int(x) for x in w.attrs['global_ids'].split(' ')]
			# highlights only count if the color changed for all words
			changed = True
			for global_id in id_group:
				# if any word in the id group was already this color, no highlight is measured
				if w.attrs['highlight'] == current_state[global_id]:
					changed = False
			# this is the case where we record stuff
			if changed:
				report[doc_time].append({
					'id':global_id,
					'text':str(w),
					'id_group':id_group,
					'color':w.attrs['highlight'],
					'former colors':[current_state[global_id] for global_id in id_group]})
				for global_id in id_group:
					current_state[global_id] = w.attrs['highlight']
	return report

# save the highlighting report to for each session
def make_highlighting_report_for_each_session(part='digital reading', redo=False):
	# get the session names
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		# avoid sessions where the corrections have not been completely calculated
		if not os.path.isfile(sess.dir_name + os.sep + 'time_to_find_highlights.json'):
			continue
		# don't recalculate
		if not redo and os.path.isfile(sess.dir_name + os.sep + 'time_to_make_highlight_report.json'):
			continue
		time_to_find_highlights = {}
		t0 = time.time()
		report = make_report(sess, part=part)
		with open(sess.dir_name + os.sep + settings.highlighting_report, 'w') as fp:
			json.dump(report, fp)
		time_to_find_highlights['make_report'] = time.time() - t0
		with open(sess.dir_name + os.sep + 'time_to_make_highlight_report.json', 'w') as fp:
			json.dump(time_to_find_highlights, fp)

# get the lengths of all words in the files
# keep track of previously calculated files
word_lengths_by_filename = {}
# calculate word lengths if they have not been previously calculated
# otherwise, return the word lengths that was stored
def get_word_lengths(filename):
	if filename not in word_lengths_by_filename:
		correct_doc_path = settings.correct_text_dir + os.sep + filename
		with open(correct_doc_path, 'r') as infile:
			text = ' '.join([line for line in infile])
			word_lengths_by_filename[filename] = [len(w) for w in text.split(' ') if len(w) > 0]
	return word_lengths_by_filename[filename]

# get the highlighting report for a user
def get_user_data(sess):
    with open(sess.dir_name + os.sep + settings.highlighting_report, 'r') as infile:
        data = json.loads(' '.join([line for line in infile]))
    return data

# get the color of a word at a time
def get_color(time, word_id, mapping, min_time):
	# if the pair is in the mapping return, the relavent value
	if (time, word_id) in mapping:
		return mapping[(time, word_id)]
	# initalize all words to white (unless mentioned in the mapping at min_time)
	if time <= min_time:
			return 'white'
	# if the pair is not in the mapping now, find the word color at a previous time
	try:
		val = get_color(time - 1, word_id, mapping, min_time)
	# figure out what is going wrong if the base case isn't being caught
	except RecursionError as e:
		print(time)
		print(word_id)
		raise e
	# save the value to the mapping so the recursion stack is shallow for future calls
	mapping[(time, word_id)] = val
	return val

# visualizing highlighting behavior over time as a matrix
# each pixel on the Y axis represents a time window of size t
# each pixel on the X asis represents a character in the article (spaces are not represented)
def get_highlight_visualization_matrix(sess, part='digital reading', redo=False):
	# load from image if not redoing and it exists
	if not redo and os.path.isfile(sess.dir_name + os.sep + settings.highlighting_image_file):
		return np.array(Image.open(sess.dir_name + os.sep + settings.highlighting_image_file))

	# get the largest reading time
	# (in the future it might be good to make multiple visualizations)
	reading_times = max([x for x in sess.metadata if x['part'] == part], key=lambda x: max(x['transitions']) - min(x['transitions']))
	reading_times = reading_times['transitions']

	if len(reading_times) == 0:
		return

	# get a sample document to find the correction document
	dir_name = sess.dir_name + os.sep + settings.highlights_dir
	sample_doc_path = dir_name + os.sep + time_to_filename(reading_times[0], extension='hocr')
	sample_doc = Document(sample_doc_path, output_dir=None)
	correction_filename = sample_doc.correct_filepath.split(os.sep)[-1]

	# get the lengths of all words
	word_lengths = get_word_lengths(correction_filename)
	total_word_length = sum(word_lengths)
	
	# get highlighting report
	data = get_user_data(sess)

	# calculate mapping from (time, word) -> color
	min_time = int(min(reading_times)/settings.little_t)
	max_time = int(max(reading_times)/settings.little_t)
	mapping = {}
	for time in data:
		for word_obj in data[time]:
			for w_id in word_obj['id_group']:
				mapping[(int(float(time) * 10), int(w_id))] = word_obj['color']
	
	# the output image (initalize to zeros)
	# this helps catch bugs as long as black is not one of the highlight colors
	matrix = np.zeros(((max_time - min_time), total_word_length, 3), 'uint8')
	
	for row in range((max_time - min_time)):
		for word_id in range(len(word_lengths)):
			color_string = get_color(row + min_time, word_id, mapping, min_time)
			# get the pixel start and end of a word
			word_start = 0 if word_id == 0 else sum(word_lengths[:word_id])
			word_end = word_start + word_lengths[word_id] + 1
			for i in range(3):
				matrix[row, word_start:word_end, i] = settings.highlight_viz_colors[color_string][i]

	# save for future calls
	img = Image.fromarray(matrix).convert('RGB')
	img.save(sess.dir_name + os.sep + settings.highlighting_image_file)
	
	# return the image
	return matrix

# make a highlighting image for each session
def make_highlighting_images(part='digital reading', redo=False):
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		# avoid sessions where there is no highlighting report
		if not os.path.isfile(sess.dir_name + os.sep + settings.highlighting_report):
			continue
		# don't recalculate
		if not redo and os.path.isfile(sess.dir_name + os.sep + 'time_to_make_highlight_image.json'):
			continue
		time_to_make_matrix = {}
		t0 = time.time()
		get_highlight_visualization_matrix(sess, part=part, redo=redo)
		time_to_make_matrix['make_matrix'] = time.time() - t0
		with open(sess.dir_name + os.sep + 'time_to_make_highlight_image.json', 'w') as fp:
			json.dump(time_to_make_matrix, fp)

# get a list of the words in the correct file to label the image with
word_labels_by_filename = {}
def get_word_labels(filename):
	if filename not in word_labels_by_filename:
		correct_doc_path = settings.correct_text_dir + os.sep + filename
		with open(correct_doc_path, 'r') as infile:
			text = ' '.join([line for line in infile])
			word_labels_by_filename[filename] = [w for w in text.split(' ') if len(w) > 0]
	return word_labels_by_filename[filename]

# make a visualization (highlight image + axis)
def make_highlight_viz(sess, words_per_label=3, part='digital reading', save_and_clear=True, include_labels=True):
	matrix = get_highlight_visualization_matrix(sess, part=part)
	max_height, max_width, _ = matrix.shape
	plt.imshow(matrix)

	# set the x ticks (words)
	# get the largest reading time
	# (in the future it might be good to make multiple visualizations)
	reading_times = max([x for x in sess.metadata if x['part'] == part], key=lambda x: max(x['transitions']) - min(x['transitions']))
	reading_times = reading_times['transitions']

	if len(reading_times) == 0:
		return

	# get a sample document to find the correction document
	dir_name = sess.dir_name + os.sep + settings.highlights_dir
	sample_doc_path = dir_name + os.sep + time_to_filename(reading_times[0], extension='hocr')
	sample_doc = Document(sample_doc_path, output_dir=None)
	correction_filename = sample_doc.correct_filepath.split(os.sep)[-1]

	# get the word labels
	word_labels = get_word_labels(correction_filename)
	# map the pixel values to words to get the labels
	word_lengths = [len(w) for w in word_labels]
	char_index_to_word_index_mapping = {}
	word_index = 0
	for char_index in range(sum(word_lengths)):
		if sum(word_lengths[:(word_index+1)]) < char_index:
			word_index += 1
		char_index_to_word_index_mapping[char_index] = word_index

	x_tick_vals = [x for x in plt.xticks()[0] if (x >= 0) and (x <= max_width)]
	x_tick_labels = []
	for x_tick in x_tick_vals:
		word_index = char_index_to_word_index_mapping[x_tick]
		last_index = min([word_index + words_per_label, len(word_labels)])
		x_tick_labels.append(' '.join(word_labels[word_index:last_index]))
	plt.xticks(x_tick_vals, x_tick_labels, rotation=15, fontsize=5)

	# set the y ticks (time)
	y_tick_vals = [y for y in plt.yticks()[0] if (y >= 0) and (y <= max_height)]
	num_to_str = lambda num: str(int(num)) if num >= 10 else '0'+str(int(num))
	to_time_str = lambda t: num_to_str(int(t/60)) + ':' + num_to_str(t-(int(t/60)*60))
	plt.yticks(y_tick_vals, [to_time_str(yt*settings.little_t) for yt in y_tick_vals])

	if include_labels:
		plt.xlabel('Article Text')
		plt.ylabel('Time')

	# add space for labels and tick marks
	plt.tight_layout()

	if save_and_clear:
		plt.savefig(sess.dir_name + os.sep + settings.highlighting_viz_file, dpi=800)
		plt.clf()

def make_highlighting_viz_for_all_sessions(part='digital reading'):
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		# make a visualization
		make_highlight_viz(sess, part=part)

if __name__ == '__main__':
	find_highlights_for_each_session()
	# make_highlighting_report_for_each_session(redo=True)
	# make_highlighting_images(redo=True)
	# make_highlighting_viz_for_all_sessions()