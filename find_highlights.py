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

def find_box_colors(xml_path, image_path):
	frame_first = cv2.imread(image_path)
	frame = cv2.fastNlMeansDenoisingColored(frame_first)
	frame = cv2.blur(frame,(2,2))
	doc = Document(xml_path)
	boxes = {}
	for line in doc.lines:
		for word in line.children:
			ids = word.attrs.get('global_ids', None)
			if ids is not None:
				ids = ids.split(' ')
				bbox = word.title['bbox']
				pixels = frame[int(bbox.top):int(bbox.bottom+1), int(bbox.left):int(bbox.right+1), :]
				roundoff = 10
				blue = np.round(pixels[:,:,0]/roundoff,0)*roundoff
				green = np.round(pixels[:,:,1]/roundoff,0)*roundoff
				red = np.round(pixels[:,:,2]/roundoff,0)*roundoff
				if '347' in ids:
					cv2.imwrite('tmp_red.png', red)
					cv2.imwrite('tmp_green.png', green)
					cv2.imwrite('tmp_blue.png', blue)
				pixels = Counter(zip(red.flatten(), green.flatten(), blue.flatten()))
				colors_found = {}
				for color in pixels:
					if pixels[color] > red.size*.01:
						colors_found[color] = float(pixels[color])/red.size
				for wid in ids:
					boxes[wid] = colors_found
	return boxes

def print_color_boxes(boxes):
	values = [(boxes[c], c) for c in boxes]
	values.sort(reverse=True)
	for val, col in values:
		print('\t{0:.2f} : {1}'.format(val, col))

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

def get_blurred_frame(image_filepath):
	frame = cv2.imread(image_filepath)
	#frame = cv2.fastNlMeansDenoisingColored(frame)
	frame = cv2.blur(frame,(2,2))
	return frame

def get_snippet(frame, bbox_info):
	left, right, top, bottom = bbox_info
	return frame[int(top):int(bottom+1), int(left):int(right+1), :]

def draw_boxes(sess, file_start):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# build the paths for each time
	xml_path = xml_dir_name + os.sep + file_start + '.hocr'
	image_path = image_dir_name + os.sep + file_start + '.jpg'
	# get word info for each word in each document
	word_info = get_word_boundries(xml_path)
	# get image
	bgr_img = cv2.imread(image_path)
	b,g,r = cv2.split(bgr_img)       # get b,g,r
	frame = cv2.merge([r,g,b])     # switch it to rgb
	# Create figure and axes
	fig, ax = plt.subplots(1)
	ax.imshow(frame)
	# plot and label each box
	for wid in word_info:
		# Create a Rectangle patch
		left, right, top, bottom, text, ids = word_info[wid]
		height = bottom-top
		width = right-left
		rect = patches.Rectangle((left,top),width,height,linewidth=.25,edgecolor='r',facecolor='none')
		ax.annotate(text, xy=(left, top), size=2, color='purple')#, xytext=(3, 1.5))
		ax.add_patch(rect)
	plt.savefig('{0}.png'.format(file_start), dpi=500)
	plt.close()

def merged_bbox(word_info, id_list):
	id_list = id_list.copy()
	final_left, final_right, final_top, final_bottom, _, _ = word_info[id_list.pop()]
	for wid in id_list:
		left, right, top, bottom, _, _ = word_info[wid]
		if left < final_left:
			final_left = left
		if top < final_top:
			final_top = top
		if right > final_right:
			final_right = right
		if bottom > final_bottom:
			final_bottom = bottom
	return final_left, final_right, final_top, final_bottom

def merge_word_info_dictionaries(word_info_1, word_info_2):
	output = {}
	ids_to_check = list(set(word_info_2.keys()) & set(word_info_1.keys()))
	while len(ids_to_check) > 0:
		wid = ids_to_check.pop()
		id_list = set(word_info_1[wid][-1] + word_info_2[wid][-1])
		need_to_add = set([x for x in id_list if x != wid])
		while len(need_to_add) > 0:
			next_id = need_to_add.pop()
			new_ids = set(word_info_1[next_id][-1] + word_info_2[next_id][-1])
			need_to_add |= (new_ids - id_list)
			id_list |= new_ids
		# assigning the correct text may be important in the future
		text = word_info_2[wid][-2]
		output[min(id_list)] = (merged_bbox(word_info_1, id_list), merged_bbox(word_info_2, id_list), text)
	return output

# just find stuff on the page that isn't white or gray
# maybe to generalize this we can just look at typical colors
# within a session and find other colors
def find_colors(sess, file_start):
	# the highlighted parts
	output = []
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# build the paths for each time
	xml_path = xml_dir_name + os.sep + file_start + '.hocr'
	image_path = image_dir_name + os.sep + file_start + '.jpg'
	# get word info for each word in each document
	word_info = get_word_boundries(xml_path)
	# get blurred frames for each time
	frame = get_blurred_frame(image_path)
	# color to text snippet map
	color_map = defaultdict(list)
	# find colors
	for wid in word_info:
		left, right, top, bottom, text, ids = word_info[wid]
		snippet = get_snippet(frame, (left, right, top, bottom))
		blue, green, red = cv2.split(snippet)
		round_num = 30
		blue = np.round(blue/round_num, 0) * round_num
		green = np.round(green/round_num, 0) * round_num
		red = np.round(red/round_num, 0) * round_num
		colors = Counter(zip(red.flatten(), green.flatten(), blue.flatten()))
		total = sum(colors.values())
		keys = colors.keys()
		for col in keys:
			colors[col] /= total
			if colors[col] < .05:
				del colors[col]
			else:
				color_map[col].append((wid, text))
	for col in color_map:
		if len(color_map[col]) > float(len(word_info)) * .3:
			print(col)
			for wid, text in color_map[col]:
				print('\t', wid, text)

def compare_frames(sess, file_start_1, file_start_2):
	# the highlighted parts
	output = []
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# build the paths for each time
	xml_path_1 = xml_dir_name + os.sep + file_start_1 + '.hocr'
	xml_path_2 = xml_dir_name + os.sep + file_start_2 + '.hocr'
	image_path_1 = image_dir_name + os.sep + file_start_1 + '.jpg'
	image_path_2 = image_dir_name + os.sep + file_start_2 + '.jpg'
	# get word info for each word in each document
	word_info_1 = get_word_boundries(xml_path_1)
	word_info_2 = get_word_boundries(xml_path_2)
	overall_info = merge_word_info_dictionaries(word_info_1, word_info_2)
	# get blurred frames for each time
	frame_1 = get_blurred_frame(image_path_1)
	frame_2 = get_blurred_frame(image_path_2)
	# find difference
	difference_threshold = 20
	for wid in overall_info:
		snippet_1 = get_snippet(frame_1, overall_info[wid][0])
		snippet_2 = get_snippet(frame_2, overall_info[wid][1])
		height = min([snippet_1.shape[0], snippet_2.shape[0]])
		width = min([snippet_1.shape[1], snippet_2.shape[1]])
		snippet_1 = snippet_1[:height, :width, :]
		snippet_2 = snippet_2[:height, :width, :]
		difference_snippet = snippet_2 - snippet_1
		average_difference = float(sum(abs(difference_snippet.flatten())))/difference_snippet.size
		if wid == '286':
			print(average_difference)
		if average_difference > difference_threshold:
			# seperate pixels according to how different they are
			part_with_difference = (difference_snippet[:,:,0] + difference_snippet[:,:,1] + difference_snippet[:,:,2]) > (average_difference)
			blue, green, red = cv2.split(snippet_2)
			round_num = 80
			blue = np.round(blue/round_num, 0) * round_num
			green = np.round(green/round_num, 0) * round_num
			red = np.round(red/round_num, 0) * round_num
			new_colors = Counter(zip(red[part_with_difference], green[part_with_difference], blue[part_with_difference]))
			total = sum(new_colors.values())
			for col in new_colors:
				new_colors[col] = float(new_colors[col])/total
			old_colors = Counter(zip(red[~part_with_difference], green[~part_with_difference], blue[~part_with_difference]))
			for col in old_colors:
				old_colors[col] = float(old_colors[col])/total
			# find the colors that weren't in the old image
			colors = new_colors.keys()
			for col in colors:
				if new_colors[col] <= old_colors.get(col, 0) * 4:
					del new_colors[col]
				else:
					new_colors[col] = new_colors[col] - old_colors.get(col, 0)
			# red[~part_with_difference] = 0
			# green[~part_with_difference] = 0
			# blue[~part_with_difference] = 0
			if len(new_colors) == 0:
				continue
			color, freq = new_colors.most_common(1)[0]
			if freq < .1:
				continue
			text = overall_info[wid][-1]
			# cv2.imwrite('tmp_{0}_{1}.png'.format(text, file_start_1), snippet_1)
			# cv2.imwrite('tmp_{0}_{1}.png'.format(text, file_start_2), snippet_2)
			output.append((text, color, freq))
	return output

def find_highlights(sess, part='digital reading'):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# if there are no hocr files to clean, we should move on
	if not os.path.isdir(xml_dir_name) or not os.path.isdir(image_dir_name):
		return
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	reading_times.sort()
	# highlights
	highlights = {}
	old_key = None
	# go through reading_times in order
	for t in reading_times:
		key = time_to_filename(t, extension='')[:-1]
		if old_key is not None:
			new_highlights = compare_frames(sess, old_key, key)
			if len(new_highlights) > 0:
				print(key)
				for pair in new_highlights:
					print(pair)
				return
				highlights[key] = new_highlights
		old_key = key
	return highlights

def find_change_between_pair(sess, file_start_1, file_start_2):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# build the paths for each time
	xml_path1 = xml_dir_name + os.sep + file_start_1 + '.hocr'
	xml_path2 = xml_dir_name + os.sep + file_start_2 + '.hocr'
	image_path1 = image_dir_name + os.sep + file_start_1 + '.jpg'
	image_path2 = image_dir_name + os.sep + file_start_2 + '.jpg'
	# get frames
	frame1 = cv2.imread(image_path1)
	frame2 = cv2.imread(image_path2)
	# get word_boundries
	doc1 = Document
	# get each set
	boxes_1 = find_box_colors(xml_path1, image_path1)
	boxes_2 = find_box_colors(xml_path2, image_path2)
	print('first')
	print_color_boxes(boxes_1['347'])
	print('second')
	print_color_boxes(boxes_2['347'])
	# print output
	# for k in boxes_2:
	# 	if k in boxes_1:
	# 		for color in boxes_2[k]:
	# 			if color not in boxes_1[k]:
	# 				print('{0} highlighted in image {1} for word {2} at percent {3:.2f}'.format(color, image_path2, k, boxes_2[k][color]))
	# 				print(boxes_1[k])
	# 				print(boxes_2[k])
	# 				return

def find_changes(sess, part='digital reading'):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	image_dir_name = sess.dir_name + os.sep + settings.frame_images_dir
	# if there are no hocr files to clean, we should move on
	if not os.path.isdir(xml_dir_name) or not os.path.isdir(image_dir_name):
		return
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	reading_times.sort()
	# use boxes to track changes
	old_boxes = {}
	# go through reading_times in order
	for t in reading_times:
		image_path = image_dir_name + os.sep + time_to_filename(t, extension='jpg')
		xml_path = xml_dir_name + os.sep + time_to_filename(t, extension='hocr')
		new_boxes = find_box_colors(xml_path, image_path)
		if old_boxes is not None:
			for k in new_boxes:
				if k in old_boxes:
					for color in new_boxes[k]:
						if color not in old_boxes[k]:
							print('{0} highlighted in image {1} for word {2} at percent {3:.2f}'.format(color, image_path, k, new_boxes[k][color]))
							print(old_boxes[k])
							print(new_boxes[k])
							return
		old_boxes = new_boxes

sess = Session('Amanda')
#find_highlights(sess)
print('blue highlight')
print(find_colors(sess, '02-55.7'))#'02-51.8')#, '02-55.7'))
# print('blue to yellow')
# print(compare_frames(sess, '02-49.5', '02-50.5'))
# print('scroll')
# print(compare_frames(sess, '02-40.3', '02-40.5'))