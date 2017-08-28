# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save output from some functions
import csv
# to build documents
from Document import Document
# to build hash table for document discovery
from collections import defaultdict

# get lists of the lines in each correct file
def get_correct_bags():
	correct_bags = {}
	for filename in os.listdir('correct_text'):
		filepath = 'correct_text' + os.sep + filename
		with open(filepath, 'r') as input_file:
			correct_bags[filename] = [l.strip() for l in input_file]
	return correct_bags

def make_matching_dictionary(correct_bags):
	word_to_doc = defaultdict(set)
	for document_name in correct_bags:
		for line in correct_bags[document_name]:
			for word in line.split(' '):
				word_to_doc[word].add(document_name)
	return word_to_doc

def cleanup_file(filepath, correct_filename=None, correct_lines=None, correct_bags=None, scale=True, redo=False):
	document = Document(filepath)
	if correct_filename is None:
		correct_filename, correct_lines = document.find_correct(correct_bags)
	else:
		document.assign_correct_bag(correct_filename, correct_lines)
	# don't re-fix files which were fixed in a previous run
	# (this is useful for when there are a lot of sessions and some throw errors)
	if not redo and os.path.isfile(document.xml_file):
		return correct_filename, correct_lines
	document.assign_lines()
	if scale:
		document.scale(settings.digital_reading_x_range[0], settings.digital_reading_y_range[0], 0.5)
	document.save()
	return correct_filename, correct_lines

# A function to clean up all the hocr files for a session
def cleanup(sess):
	correct_bags = get_correct_bags()
	dir_name = sess.dir_name + os.sep + settings.hocr_dir
	correct_filename = None
	correct_lines = None
	# don't bother with sessions which don't have any hocr files
	if not os.path.isdir(dir_name):
		return
	for filename in os.listdir(dir_name):
		filepath = dir_name + os.sep + filename
		if correct_filename is None:
			correct_filename, correct_lines = cleanup_file(filepath, correct_filename, correct_lines, correct_bags)
		else:
			correct_filename, correct_lines = cleanup_file(filepath, correct_filename, correct_lines)

def find_percent_correct(sess):
	correct_bags = get_correct_bags()
	dir_name = sess.dir_name + os.sep + settings.hocr_dir
	correct_filename = None
	correct_lines = None
	precent_correct = []
	# don't bother with sessions which don't have any hocr files
	if not os.path.isdir(dir_name):
		return
	for filename in os.listdir(dir_name):
		filepath = dir_name + os.sep + filename
		document = Document(filepath)
		if len(document.lines) == 0:
			continue
		if correct_filename is None:
			correct_filename, correct_lines = document.find_correct(correct_bags)
		else:
			document.assign_correct_bag(correct_filename, correct_lines)
		precent_correct.append(document.percent_of_initial_correct())
	print 'mean:', np.mean(precent_correct)
	print 'std:', np.std(precent_correct)

if __name__ == '__main__':
	doc = Document('test-data/14-34.8.hocr', 'test-output')
	correct_bags = get_correct_bags()
	doc.find_correct(correct_bags, make_matching_dictionary(correct_bags))
	doc.assign_lines(testing=True)
	doc.calc_char_width()
	for l in doc.lines:
		l.initial_mapping(testing=True)
		l.assign_words(testing=True)
	
