# to read in files
import os
# to turn pictures from Piazza! into text which can be mapped to the text found in participant frame images
import initial_ocr
# to clean up tessaract reading of Piazza! image
import ocr_cleanup
# to read in xml files
import pair_screen_with_eyes
# to get the session info
from video_to_frames import Session
# to store values
from collections import defaultdict
# to investigate distributions
from collections import Counter
# for making and reading images
from matplotlib import pyplot as plt
from PIL import Image
# to save mapped values
import csv
# to interpret csv data as objects
from collections import namedtuple
# to make heatmaps
import numpy as np
# to resize heatmaps to overlap images
from scipy import ndimage
# to define things once
import settings

def images_to_xml():
	# Run tesseract on the website images
	image_dir = 'parts_for_viz'+os.sep+'resized-images'
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(image_dir):
		image_path = image_dir + os.sep + filename
		hocr_path = hocr_dir + os.sep + filename
		initial_ocr.run_tesseract_on_image(image_path, hocr_path)
	# Cleanup the tesseract output
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(hocr_dir):
		hocr_path = hocr_dir + os.sep + filename
		# turn off scaling since in this instance tesseract was run on the original image
		ocr_cleanup.cleanup_file(hocr_path, correct_bags=ocr_cleanup.get_correct_bags(), scale=False)

def get_viz_documents():
	viz_documents = {}
	xml_dir = 'parts_for_viz'+os.sep+'xml-files'
	for filename in os.listdir(xml_dir):
		xml_path = xml_dir + os.sep + filename
		viz_documents[filename] = pair_screen_with_eyes.Document(xml_path, None)
	return viz_documents

# this function produces a function which maps a point in a frame image to
# a point on the image of the correct document which we made with piazza
def get_mapping_function(frame_document, viz_document_dict):
	correct_doc = frame_document.correct_filepath
	# I should change this so it isn't hardcoded in the future
	viz_document = viz_document_dict['womens_suffrage_1_B.png.xml'] if '1' in correct_doc else viz_document_dict['womens_suffrage_2_A.png.xml']
	try:
		non_empty_lines = [l for l in frame_document.lines if len(l.updated_line) > 0]
		frame_top, viz_top = point_values(non_empty_lines[1], viz_document, top=True)
		bottom_index = len(non_empty_lines)-2
		frame_bottom, viz_bottom = point_values(non_empty_lines[bottom_index], viz_document, top=False)
		while bottom_index > 1 and frame_bottom[0] <= frame_top[0]:
			bottom_index -= 1
			frame_bottom, viz_bottom = point_values(non_empty_lines[bottom_index], viz_document, top=False)
	except Exception as e:
		print 'Error raised while matching file '+frame_document.xml_filepath
		raise e
	if frame_bottom[0] == frame_top[0]:
		print frame_document.xml_filepath
		print bottom_index
		print non_empty_lines[1].bbox
		print non_empty_lines[-2].bbox
		raise Exception('frame_bottom = '+str(frame_bottom)+' and frame_top = '+str(frame_top))
	x_fun = lambda x : (x-frame_top[0])*float(viz_bottom[0]-viz_top[0])/(frame_bottom[0]-frame_top[0]) + viz_top[0]
	y_fun = lambda y : (y-frame_top[1])*float(viz_bottom[1]-viz_top[1])/(frame_bottom[1]-frame_top[1]) + viz_top[1]
	return lambda x,y : (x_fun(x), y_fun(y))

# to get the change function from one to the other
def point_values(line_src, dst_document, top):
	dst_index = None
	for i in range(len(dst_document.lines)):
		if dst_document.lines[i].updated_line == line_src.updated_line:
			dst_index = i
			break
	if dst_index is None:
		raise Exception(str(line_src)+' has no match')
	x_src, y_src = get_x_and_y(line_src, top)
	x_dst, y_dst = get_x_and_y(dst_document.lines[dst_index], top)
	return (x_src, y_src), (x_dst, y_dst)

# this is based on the line level not the word level which 
# might be problematic if a pop-up is covering half of the line
def get_x_and_y(line_val, top):
	x = line_val.bbox.left if top else line_val.bbox.right
	y = line_val.bbox.top if top else line_val.bbox.bottom
	return x, y

def calculate_mapped_values_and_save(sess):
	# get the pairing of gaze data with OCR interpreted frames
	corpus = pair_screen_with_eyes.Corpus(sess)
	row_list = pair_screen_with_eyes.get_eye_tracking_rows(sess)
	document_assignment = corpus.assign_rows(row_list)
	viz_document_dict = get_viz_documents()
	with open(sess.dir_name + os.sep + settings.eye_tracking_mapped_csv_file, 'w') as output_file:
		# open a csv to write into
		writer = csv.writer(output_file, delimiter=',', quotechar='"')
		# write a header
		writer.writerow(['Mapped_X', 'Mapped_Y', 'Timestamp', 'MediaTime'])
		# initialize values to None
		mapping_function = None
		frame_document_index = None
		for pair in document_assignment:
			row = pair[0]
			if int(row.GazeX) < 0 or int(row.GazeY) < 0:
				continue
			if pair[1] != frame_document_index:
				# this is the xml for the frame
				frame_document = corpus.documents[pair[1]]
				mapping_function = get_mapping_function(frame_document, viz_document_dict)
			mapped_x, mapped_y = mapping_function(int(row.GazeX), int(row.GazeY))
			writer.writerow([mapped_x, mapped_y, row.Timestamp, row.MediaTime])

def make_heatmap(session_names, dst_img_path):
	# initialize everything
	dst_img = Image.open(dst_img_path)
	horz, vert = dst_img.size
	bins = np.zeros([(vert/settings.pixels_per_bin)+1, (horz/settings.pixels_per_bin)+1])
	# put the data into the bins
	for sess_name in session_names:
		sess = Session(sess_name)
		with open(sess.dir_name + os.sep + settings.eye_tracking_mapped_csv_file, 'r') as in_file:
			reader = csv.reader(in_file, delimiter=',', quotechar='"')
			row_obj = None
			for row in reader:
				if row_obj is None:
					row_obj = namedtuple('row_obj', list(row))
					continue
				row = row_obj(*tuple(row))
				x = float(row.Mapped_X)
				y = float(row.Mapped_Y)
				if x < 0 or x > horz or y < 0 or y > vert:
					continue
				x_index = int(x/settings.pixels_per_bin)
				y_index = int(y/settings.pixels_per_bin)
				bins[y_index, x_index] += 1
	return bins

def bin_heatmap(heatmap, parts=4):
	# figure out where to put dividers to make equally sized bins
	value_counts = Counter(list(heatmap.flatten()))
	total = sum(value_counts.values())

	keys = value_counts.keys()
	keys.sort()

	cuttoffs = []
	sum_total = 0

	for k in keys:
		sum_total += value_counts[k]
		if sum_total >= float(total)/parts:
			cuttoffs.append(k)
			sum_total = 0

	# calculate which bin each cell is in
	output = np.zeros(heatmap.shape)
	for i in range(len(cuttoffs)):
		if i == len(cuttoffs)-1:
			output[heatmap > cuttoffs[i]] = i+1
		else:
			output[(heatmap > cuttoffs[i]) & (output <= cuttoffs[i+1])] = i+1
	return output, cuttoffs

def plot_heatmap(bins, dst_img_path, output_path, parts=4):
	dst_img = Image.open(dst_img_path)
	# bin for better viewing
	binned_headmap, cuttoffs = bin_heatmap(bins, parts)
	heatmap_image = ndimage.zoom(binned_headmap, settings.pixels_per_bin, order=0)
	# make the plot
	fig = plt.figure()
	ax = fig.add_subplot(1,1,1)
	ax.imshow(dst_img)
	cax = ax.imshow(heatmap_image, cmap=plt.cm.gray, interpolation='nearest', alpha=.5)
	# get rid of axes
	ax.set_xticks([])
	ax.set_yticks([])
	# Add colorbar, make sure to specify tick locations to match desired ticklabels
	# We need to define boundries to avoid getting a continuous color bar
	boundaries = [0] + [x+.5 for x in range(len(cuttoffs))] + [parts-1]
	cbar = fig.colorbar(cax, ticks=range(parts), boundaries=boundaries)
	# strings to describe each bin
	labels = ['<='+str(int(cuttoffs[0]))]
	labels += [str(int(cuttoffs[i-1])+1)+'-'+str(int(cuttoffs[i])) for i in range(1,len(cuttoffs))]
	labels.append('>='+str(int(cuttoffs[-1])+1))
	cbar.ax.set_yticklabels(labels)  # vertically oriented colorbar
	ax.set_title('Number of Fixations')
	plt.savefig(output_path, dpi=800)

# visualize scrolling
def get_scroll(sess, xml_dir_extention=None):
	# get the corpus
	corpus = pair_screen_with_eyes.Corpus(sess, xml_dir_extention=xml_dir_extention)
	if len(corpus.documents) == 0:
		return [], None
	# get the correct document for this corpus
	viz_document_dict = get_viz_documents()
	data = []
	# calculate the correct file for visualizing
	correct_doc = corpus.documents[0].correct_filepath
	# retrieve the time and top of page values for each document
	for doc in corpus.documents:
		t = doc.time
		mapping_function = get_mapping_function(doc, viz_document_dict)
		_, y_top = mapping_function(500, settings.y_range['digital reading'][0])
		_, y_bottom = mapping_function(500, settings.y_range['digital reading'][1])
		data.append((t,y_top, y_bottom))
	return data, correct_doc

def plot_scroll(sess, xml_dir_extention=None):
	# make sure there is nothing still in the figure
	plt.cla()
	# get the scrolling data
	data, correct_doc = get_scroll(sess, xml_dir_extention=xml_dir_extention)
	if len(data) == 0:
		return
	# expand the data to cover the full time period for each frame
	data += [(data[i][0]-.05, data[i-1][1], data[i-1][2]) for i in range(1,len(data))]
	data.sort()
	# load an image of the file
	dst_img_path = 'parts_for_viz/resized-images/womens_suffrage_'
	dst_img_path += '1_B.png' if correct_doc.find('1') != -1 else '2_A.png'
	dst_img = Image.open(dst_img_path)
	width, height = dst_img.size
	# visualize image
	plt.imshow(dst_img)
	# plot data on top
	x_vals, y_top_vals, y_bottom_vals = zip(*data)
	x_vals_scaled = [(x-min(x_vals))/(max(x_vals)-min(x_vals))*width for x in x_vals]
	plt.plot(x_vals_scaled, y_top_vals, 'b')
	plt.plot(x_vals_scaled, y_bottom_vals, 'b')
	plt.xlabel('Time')
	plt.ylabel('Top and Bottom of Screen')
	# fix x ticks
	x_tick_vals = plt.xticks()[0]
	x_tick_vals_unscaled = [x/width*(max(x_vals)-min(x_vals))+min(x_vals) for x in x_tick_vals]
	num_to_str = lambda num: str(int(num)) if num >= 10 else '0'+str(int(num))
	to_time_str = lambda t: num_to_str(int(t)/60) + ':' + num_to_str(t-((int(t)/60)*60))
	plt.xticks(x_tick_vals, [to_time_str(xt) for xt in x_tick_vals_unscaled])
	# get rid of y ticks
	plt.yticks([], [])
	plt.savefig(sess.dir_name + os.sep + 'scrolling.png', dpi=800)

if __name__ == '__main__':
	# some session ids from the pilot data
	session_even_names = ['second_student_participant', 'sixth_participant'] # 'eighth_participant', 'fourth-participant-second-version', 
	session_odd_names = ['fifth_participant', 'first_student_participant_second_take','seventh_participant', 'third_student_participant']

	for sess_name in session_even_names + session_odd_names:
		print sess_name
		sess = Session(sess_name)
		if not os.path.isdir(sess.dir_name + os.sep + 'hocr-files'):
			print 'no hocr'
			continue
		if not os.path.isdir(sess.dir_name + os.sep + 'xml-files'):
			print 'no xml'
			continue
		hocr_files = len(os.listdir(sess.dir_name + os.sep + 'hocr-files'))
		xml_files = len(os.listdir(sess.dir_name + os.sep + 'xml-files'))
		if hocr_files == xml_files:
			plot_scroll(sess)
		else:
			print hocr_files, xml_files
	
	# heatmap = make_heatmap(session_odd_names, 'parts_for_viz/resized-images/womens_suffrage_2_A.png')
	# plot_heatmap(heatmap, 'parts_for_viz/resized-images/womens_suffrage_2_A.png', 'womens_suffrage_2_A_heatmap.png', parts=5)

	# heatmap = make_heatmap(session_even_names, 'parts_for_viz/resized-images/womens_suffrage_1_B.png')
	# plot_heatmap(heatmap, 'parts_for_viz/resized-images/womens_suffrage_1_B.png', 'womens_suffrage_1_B_heatmap.png', parts=5)

