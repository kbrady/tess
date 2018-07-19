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
# to read in images
import cv2
# to visualize stuff
from matplotlib import pyplot as plt
import matplotlib.patches as patches

def get_word_boundries(doc_filepath):
	doc = Document(doc_filepath)
	word_series = [word for line in doc.lines for word in line.children]
	output = {}
	for word in word_series:
		ids = word.attrs.get('global_ids', None)
		if ids is None:
			continue
		ids = ids.split(' ')
		for wid in ids:
			bbox = word.title['bbox']
			output[wid] = (bbox.left, bbox.right, bbox.top, bbox.bottom, str(word), ids)
	return output

def get_lower_and_upper(color):
	amount = 10
	lower = [max([0, val-amount]) for val in color]
	upper = [min([255, val+amount]) for val in color]
	reorder = lambda col: np.array(col, dtype='uint')
	return reorder(lower), reorder(upper)

def find_highlights(sess, file_start):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# build the paths for each time
	xml_path = xml_dir_name + os.sep + file_start + '.hocr'
	image_path = image_dir_name + os.sep + file_start + '.jpg'
	# get word info for each word in each document
	word_info = get_word_boundries(xml_path)
	already_found = set({})
	# store results
	results = []
	# get image
	bgr_img = cv2.imread(image_path)
	b,g,r = cv2.split(bgr_img)       # get b,g,r
	frame = cv2.merge([r,g,b])     # switch it to rgb
	# find highlights
	for h_color in settings.highlight_colors:
		lower, upper = get_lower_and_upper(h_color)
		mask = cv2.inRange(frame, lower, upper)
		# maybe get rid of this hard coding and use the smallest word size instead
		if sum(mask.flatten()) < 30:
			continue
		for wid in word_info:
			# skip ids that highlights have alreday been found for
			if wid in already_found:
				continue
			# Create a Rectangle patch
			left, right, top, bottom, text, ids = word_info[wid]
			size = (bottom - top) * (right - left)
			# check if highlighted area is at least 10 pixels
			if sum(mask[int(top):int(bottom+1), int(left):int(right+1)].flatten())/255 > 10:
				for id_num in ids:
					already_found.add(id_num)
				results.append((h_color, text, ids))
	return results

# after highlights are found write them to the document so they can be seen in the xml
def add_highlights_to_document(sess, file_start, found_highlights):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	# build the paths for each time
	xml_path = xml_dir_name + os.sep + file_start + '.hocr'
	# build path for highlights files
	with_highlights_dir_name = sess.dir_name + os.sep + settings.highlights_dir
	# if the directory path doesn't exist, make it
	doc = Document(xml_path, output_dir = with_highlights_dir_name)
	# make a mapping from each word to its ids
	word_mapping = {}
	word_series = [word for line in doc.lines for word in line.children]
	for word in word_series:
		ids = word.attrs.get('global_ids', None)
		if ids is None:
			continue
		ids = str(set(ids.split(' ')))
		word_mapping[ids] = word
	# set highlights
	for color, text, ids in found_highlights:
		word_mapping[str(set(ids))].attrs['highlight'] = str(color)
	# save document
	doc.save()

# find highlights for a session
def find_all_session_highlights(sess, part='digital reading'):
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	for t in reading_times:
		filename_start = time_to_filename(t, extension='')[:-1]
		answer = find_highlights(sess, filename_start)
		add_highlights_to_document(sess, filename_start, answer)

# make a report of when highlights were made and editted
def make_report(sess, part='digital reading'):
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	reading_times.sort()
	report = defaultdict(dict)
	highlighted_ids = {}
	dir_path = sess.dir_name + os.sep + settings.highlights_dir + os.sep
	for t in reading_times:
		new_highlight_ids = {}
		doc = Document(dir_path + time_to_filename(t, extension='hocr'))
		words = [w for l in doc.lines for w in l.children if 'highlight' in w.attrs]
		# find new and changed highlights
		new_highlights = []
		changed_highlights = []
		all_current_ids = []
		for w in words:
			highlight_color = w.attrs['highlight']
			ids = w.attrs.get('global_ids', None)
			if ids is None:
				raise Exception('Word %s (%s) has highlight but no id'.format(str(w), str(w.attrs)))
			ids = ids.split(' ')
			new = True
			for w_id in ids:
				all_current_ids.append(w_id)
				new_highlight_ids[w_id] = (highlight_color, ids, str(w))
				# find out if this highlight is new
				if w_id in highlighted_ids:
					# find out if this highlight has changed
					# only if we haven't already checked (new = True)
					if new and highlighted_ids[w_id][0] != highlight_color:
						changed_highlights.append((ids, str(w), highlight_color))
					new = False
			if new:
				new_highlights.append((ids, str(w), highlight_color))
		# find deleted highlights
		deleted_highlights = []
		# get a lit of all the ids in the document
		ids_in_doc = [w_id for l in doc.lines for w in l.children for w_id in w.attrs.get('global_ids', '').split(' ') if len(w_id) > 0]
		for w_id in highlighted_ids:
			if w_id not in all_current_ids:
				# check if not part of a word that is in the current ids
				highlight_color, other_ids, text = highlighted_ids[w_id]
				found_other_id = None
				for other_w_id in other_ids:
					if other_w_id in all_current_ids:
						found_other_id = other_w_id
						break
				if found_other_id is not None:
					continue
				# check if id in current document (may have moved off page)
				if w_id in ids_in_doc:
					deleted_highlights.append((other_ids, text, highlight_color))
				else:
					new_highlight_ids[w_id] = (highlight_color, other_ids, str(w))
		# update the highlights dictionary
		highlighted_ids = new_highlight_ids
		# add to report if anything was found
		if len(deleted_highlights) > 0:
			deleted_highlights.sort()
			report[t]['delted'] = deleted_highlights
		if len(changed_highlights) > 0:
			changed_highlights.sort()
			report[t]['changed'] = changed_highlights
		if len(new_highlights) > 0:
			new_highlights.sort()
			report[t]['new'] = new_highlights
	return report

if __name__ == '__main__':
	for sess_name in os.listdir('data'):
		if sess_name.startswith('.'):
			continue
		print(sess_name)
		sess = Session(sess_name)
		report = make_report(sess)
		keys = report.keys()
		keys.sort()
		for t in keys:
			time_key = time_to_filename(t, extension='')
			print('\t{0}'.format(time_key))
			print('\t{0}'.format(str(report[t])))
	# for sess_name in os.listdir('data'):
	# 	if sess_name.startswith('.'):
	# 		continue
	# 	print(sess_name)
	# 	sess = Session(sess_name)
	# 	find_all_session_highlights(sess)