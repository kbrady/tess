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
				# print(h_color, left, right, top, bottom, text)
				# sub_frame = bgr_img[int(top):int(bottom+1), int(left):int(right+1), :]
				# sub_mask = mask[int(top):int(bottom+1), int(left):int(right+1)]
				# print(mask.shape)
				# print(sub_frame.shape)
				# output = cv2.bitwise_and(sub_frame, sub_frame, mask = sub_mask)
				# cv2.imwrite('tmp_{0}.png'.format(text), output)
				# print(sum(mask[int(top):int(bottom+1), int(left):int(right+1)].flatten())/255)
				# print(size)
				# print(sum(mask[int(top):int(bottom+1), int(left):int(right+1)].flatten())/255/size)
	return results

sess = Session('Amanda')
results = []
for filename in os.listdir('data/Amanda/with-id-files/'):
	time_snippet = filename[:-5]
	answer = find_highlights(sess, time_snippet)
	if len(answer) > 0:
		results.append((time_snippet, answer))
results.sort()
for r in results:
	print(r)