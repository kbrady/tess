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

# to determine if a line is outside the bounds of known lines
def valid_line(bbox, right_dimensions, left_dimensions):
	def in_bounds(val, dim):
		return val <= (dim.max + dim.std) and val >= (dim.min - dim.std)
	return in_bounds(bbox.right, right_dimensions) and in_bounds(bbox.left, left_dimensions)

# to match words which were incorrect
def assign(set_to_assign, all_strings, complete_coverage=False):
	# to sort the words by how well they match
	def zip_indexes(word_tuple, matching_tuple):
		if complete_coverage:
			word_index = word_tuple[0]
			matching_index = matching_tuple[2]
			normalized_diff = float(abs(word_index - matching_index))/len(set_to_assign)
		else:
			normalized_diff = 0
		match_diff = matching_tuple[0]
		return normalized_diff + match_diff
	def edge_of_assignment(match_index, comparison):
		return len([i for i in range(len(assignment)) if comparison(i,match_index) and assignment[i] != -1]) == 0
	words = [(i, set_to_assign[i]) for i in range(len(set_to_assign))]
	matchings = [w.find_matching(all_strings) for w in set_to_assign]
	together = zip(words, matchings)
	together = [(zip_indexes(*tuple(x)), x) for x in together]
	together.sort()
	# assign the strings to the words they will be assigned to
	assignment = [-1] * len(all_strings)
	for pairing in together:
		match_index = pairing[1][1][2]
		word_index = pairing[1][0][0]
		if assignment[match_index] != -1:
			continue
		largest_before = [x for x in assignment[:match_index] if x != -1]
		if len(largest_before) > 0 and max(largest_before) > word_index:
			continue
		smallest_after = [x for x in assignment[match_index:] if x != -1]
		if len(smallest_after) > 0 and min(smallest_after) < word_index:
			continue
		assignment[match_index] = word_index
	for match_index in range(len(assignment)):
		# don't find a match if one has already been found
		if assignment[match_index] != -1:
			continue
		# find the latest assigned word before this one
		before_index = match_index - 1
		before = None if before_index < 0 else assignment[before_index]
		while before == -1:
			before_index -= 1
			before = None if before_index < 0 else assignment[before_index]
		# find the earliest assigned word after this one
		after_index = match_index + 1
		after = None if after_index >= len(assignment) else assignment[after_index]
		while after == -1:
			after_index += 1
			after = None if after_index >= len(assignment) else assignment[after_index]
		# if no word was assigned before this one, assign this word to the greater of
		# the earliest slot found after minus the difference between this word and that one
		# and 0
		if before is None:
			assignment[match_index] = max(after - (after_index - match_index), 0)
			continue
		# if no word was assigned after this one, assign this word to the lesser of
		# the latest word found before plus the difference between this word and that one
		# and the last index
		if after is None:
			assignment[match_index] = min(before + (match_index - before_index), len(set_to_assign)-1)
			continue
		# if a word was found before and a word was found after, get both possible positions
		# note that our minimum value is before and our maximum value is after
		# (not 0 and the length of the list)
		before_val = min(before + (match_index - before_index), after)
		after_val = max(after - (after_index - match_index), before)
		# if the two possible positions are the same, assign the word to that position
		if before_val == after_val:
			assignment[match_index] = before_val
		# otherwise assign it to the position it has a closer lexical distance to
		else:
			before_diff = set_to_assign[before_val].levenshteinDistance(all_strings[match_index])
			after_diff = set_to_assign[after_val].levenshteinDistance(all_strings[match_index])
			if before_diff < after_diff:
				assignment[match_index] = before_val
			else:
				assignment[match_index] = after_val
	for word_index in range(len(set_to_assign)):
		condition = lambda match_index: assignment[match_index] == word_index
		matching_strings = [all_strings[i] for i in range(len(assignment)) if condition(i)]
		text = ' '.join(matching_strings)
		set_to_assign[word_index].assign_matching(text)

# get lists of the lines in each correct file
def get_correct_bags():
	correct_bags = {}
	for filename in os.listdir('correct_text'):
		filepath = 'correct_text' + os.sep + filename
		with open(filepath, 'r') as input_file:
			correct_bags[filename] = [l.strip() for l in input_file]
	return correct_bags

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
	doc = Document('test-data/doc-1-sidebar.hocr', 'test-output')
	correct_bags = get_correct_bags()
	doc.find_correct(correct_bags)
	doc.assign_lines(testing=True)
	doc.calc_char_width(testing=True)
	"""
	line_dict = dict([(l.id,l) for l in doc.lines])
	my_line = line_dict['line_1_7']
	pairing = my_line.initial_mapping()
	ocr_index = 2
	print 'start', my_line.difference_function(ocr_index, pairing)
	for split_1 in range(len(pairing[ocr_index])+1):
		for split_2 in range(split_1,len(pairing[ocr_index])+1):
			print split_1, split_2, my_line.difference_function(ocr_index, pairing, split_1, split_2)
	
	word_dict = dict([(w.id, w) for l in doc.lines for w in l.children])
	my_word = word_dict['word_1_36']
	prev_word = word_dict['word_1_35']
	next_word = word_dict['word_1_37']
	# first test
	
	# calculate total distance
	difference = prev_word.match_difference('Women Get')
	difference += my_word.match_difference('the Vote')
	difference += next_word.match_difference('')
	print 'first', difference
	# calculate total distance
	difference = prev_word.match_difference('Women Get')
	difference += my_word.match_difference('the')
	difference += next_word.match_difference('Vote')
	print 'second', difference
	"""
	for l in doc.lines:
		l.assign_words(testing=True)
	
