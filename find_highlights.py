# to fix matplotlib errors
import matplotlib
matplotlib.use('Agg')
# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename
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
def seperate_image(img, method=threshold_img):
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
	img_segment = img[top:bottom, left:right, :]
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
			if 'global_ids' not in word.attrs or len(word.attrs['global_ids']) == 0:
				continue
			find_highlight_color(word, img, no_bolding = no_bolding)
	doc.save()

# find the highlight colors for a session
def find_all_highlights(sess, part='digital reading', no_bolding = False):
	# directory to read documents from
	with_ids_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	# build path for highlights files
	with_highlights_dir_name = sess.dir_name + os.sep + settings.highlights_dir
	# get directory to pull images from
	img_dir_path = sess.dir_name + os.sep + settings.frame_images_dir
	# get times for each document
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	for t in reading_times:
		xml_path = with_ids_dir_name + os.sep + time_to_filename(t, extension='hocr')
		doc = Document(xml_path, output_dir = with_highlights_dir_name)
		find_highlights(doc, img_dir_path, no_bolding = no_bolding)

# make a report of when highlights were made and editted
def make_report(sess, part='digital reading'):
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	reading_times.sort()
	report = defaultdict(list)
	# keep track of the current state of each word
	# assume the starting color is white
	current_state = defaultdict(lambda:'white')
	dir_path = sess.dir_name + os.sep + settings.highlights_dir + os.sep
	for t in reading_times:
		new_highlight_ids = {}
		doc = Document(dir_path + time_to_filename(t, extension='hocr'))
		words = [w for l in doc.lines for w in l.children if 'highlight' in w.attrs]
		for w in words:
			# if there is no global id, skip
			if 'global_ids' not in w.attrs:
				continue
			# treat each global id as different
			id_group = [int(x) for x in w.attrs['global_ids'].split(' ')]
			for global_id in id_group:
				# this is the case where we record stuff
				if w.attrs['highlight'] != current_state[global_id]:
					# don't count white to light blue since we get a lot of false possitives here
					# THIS IS HARD CODED SHOULD FIX
					if w.attrs['highlight'] == 'light blue' and current_state[global_id] == 'white':
						continue
					report[t].append({
						'id':global_id,
						'text':str(w),
						'id_group':id_group,
						'color':w.attrs['highlight'],
						'former color':current_state[global_id]})
					current_state[global_id] = w.attrs['highlight']
	return report

if __name__ == '__main__':
	for sess_name in os.listdir('data'):
		if sess_name.startswith('.'):
			continue
		sess = Session(sess_name)
		find_all_highlights(sess)
		report = make_report(sess)
		print(sess_name, len(report))
		with open(sess_name + '.json', 'w') as outfile:
			outfile.write(json.dumps(report))