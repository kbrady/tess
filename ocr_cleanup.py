# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names
# to read hocr files and write xml files
from bs4 import BeautifulSoup
# to write corrected output to file
import xml.etree.cElementTree as ET
# to make word frequency vectors and store dimensions
from collections import Counter, namedtuple
# to convert characters to ascii
import unicodedata
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np

# to handle unicode characters that unicodedata doesn't catch
Replacement_Dict = {u'\u2014':'-'}

def replace_unicode(text):
	for k in Replacement_Dict:
		text = text.replace(k, Replacement_Dict[k])
	return text

# a class to store, interpret and scale bounding boxes
class BBox:
	def __init__(self, info):
		if type(info) == str or type(info) == unicode:
			info = [int(x) for x in info.split(' ')]
		try:
			self.right, self.top, self.left, self.bottom = info
		except Exception as e:
			print type(info)
			print info
			raise e

	def __str__(self):
		return ' '.join([str(x) for x in [self.right, self.top, self.left, self.bottom]])

	def scale(self, right_shift, down_shift, multiple):
		# stretch by multiple
		self.right *= multiple
		self.left *= multiple
		self.top *= multiple
		self.bottom *= multiple
		# shift right and left by right_shift
		self.right += right_shift
		self.left += right_shift
		# shift top and bottom by down shift
		self.top += down_shift
		self.bottom += down_shift

# A parent object for lines and words which defines some shared functionality
class Part(object):
	def __init__(self, tag):
		info = tag['title'].split('; ')
		self.bbox = BBox(info[0][info[0].find(' ')+1:])
		self.id = tag['id']

	# this is can be a fuzzy match
	# we'd like to match sub-strings for lines but full strings for words
	# sometimes we have the full line but not always
	def levenshteinDistance(self, s2):
		s1 = str(self)
		if len(s1) == 0:
			return 1.0

		# if we are matching lines we are interested in sub-strings
		# but in the word case it costs us more to add letters to
		# s1 (this string) than s2 (the word)
		cost_of_skipping_s2_letters = 1
		cost_of_skipping_s1_letters = 1.5
		cost_of_substatuting_letters = 1
		distances = [v*cost_of_skipping_s1_letters for v in range(len(s1) + 1)]
		for i2, c2 in enumerate(s2):
			# cost of starting here and skipping the rest of s2
			distances_ = [distances[0] + cost_of_skipping_s2_letters]
			for i1, c1 in enumerate(s1):
				if c1 == c2:
					distances_.append(distances[i1])
				else:
					skip_this_letter_in_s2 = distances[i1] + cost_of_skipping_s2_letters
					skip_this_letter_in_s1 = distances_[-1] + cost_of_skipping_s1_letters
					substatute_this_letter = distances[i1 + 1] + cost_of_substatuting_letters
					distances_.append(min((skip_this_letter_in_s2, skip_this_letter_in_s1, substatute_this_letter)))
			distances = distances_
		return float(distances[-1])/len(s1)

	# this is used to match words not lines
	def find_matching(self, all_strings):
		all_strings = [(self.levenshteinDistance(all_strings[i]), all_strings[i], i) for i in range(len(all_strings))]
		return min(all_strings)

# An object to interpret words in hocr files
class Word(Part):
	def __init__(self, tag, et_parent=None):
		super(self.__class__, self).__init__(tag)
		# set text and clean up by changing all text to ascii (assuming we are working in English for the moment)
		self.text = tag.get_text()
		self.text = replace_unicode(self.text)
		self.text = unicodedata.normalize('NFKD', self.text).encode('ascii','ignore')
		self.corrected_text = None
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, "word", bbox=str(self.bbox))
		else:
			self.et = ET.Element("word", bbox=str(self.bbox))
		self.et.text = self.text

	def __repr__(self):
		if self.corrected_text is not None:
			return self.corrected_text
		return ''.join(filter(lambda x:ord(x) < 128, self.text))

	def assign_matching(self, text):
		self.corrected_text = text
		self.et.text = text

	def scale(self, right_shift, down_shift, multiple):
		self.bbox.scale(right_shift, down_shift, multiple)
		self.et.set('bbox', str(self.bbox))

# An object to interpret lines in hocr files
class Line(Part):
	def __init__(self, tag, et_parent=None):
		super(self.__class__, self).__init__(tag)
		self.updated_line = '' 
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, "line", bbox=str(self.bbox))
		else:
			self.et = ET.Element("line", bbox=str(self.bbox))
		self.children = [Word(sub_tag, self.et) for sub_tag in tag.find_all('span', {'class':'ocrx_word'})]
		self.word_hist = Counter([str(c) for c in self.children])
		self.letter_hist = Counter(str(self))
	
	def __repr__(self):
		return ' '.join([str(word) for word in self.children])

	# I am making a line specific implementation of this so we can have fuzzy
	# matching for substrings (the whole line is sometimes not visible due to sidebar etc.)
	def levenshteinDistance(self, s2, s2_edge_cost=.01, s2_mid_cost=1, s1_cost=1, sub_cost=1):
		s1 = str(self)
		if len(s1.strip()) == 0:
			return 1.0

		# if we are matching lines we are interested in sub-strings
		# but in the word case it costs us more to add letters to
		# s1 (this string) than s2 (the word)
		cost_of_skipping_edge_s2_letters = s2_edge_cost
		cost_of_skipping_mid_s2_letters = s2_mid_cost
		cost_of_skipping_s1_letters = s1_cost
		cost_of_substatuting_letters = sub_cost
		distances = [v*cost_of_skipping_edge_s2_letters for v in range(len(s2) + 1)]
		for i1, c1 in enumerate(s1):
			# cost of starting here and skipping the rest of s2
			distances_ = [distances[0] + cost_of_skipping_s1_letters]
			for i2, c2 in enumerate(s2):
				if c1 == c2:
					# indexes are off by one since we start with the null position so this is
					# actually the value diaganally upwards from the current position
					distances_.append(distances[i2])
				else:
					skip_this_letter_in_s1 = distances[i2] + cost_of_skipping_s1_letters
					skip_this_letter_in_s2 = distances_[-1] + cost_of_skipping_mid_s2_letters
					substatute_this_letter = distances[i2 + 1] + cost_of_substatuting_letters
					distances_.append(min((skip_this_letter_in_s2, skip_this_letter_in_s1, substatute_this_letter)))
			distances = distances_
		# we need a final row on the bottom like the one on the top to add the cost of edge skips at the end
		final_distances = [distances[i]+(len(distances)-i-1)*cost_of_skipping_edge_s2_letters for i in range(len(distances))]
		return float(min(final_distances))/len(s1)

	def assign_matching(self, string):
		self.updated_line = string
		if len(string) > 0:
			assign(self.children, string.split(' '), complete_coverage=True)
		else:
			for word in self.children:
				word.assign_matching('')

	def scale(self, right_shift, down_shift, multiple):
		self.bbox.scale(right_shift, down_shift, multiple)
		self.et.set('bbox', str(self.bbox))
		for word in self.children:
			word.scale(right_shift, down_shift, multiple)

# An object to interpret hocr files
class Document:
	def __init__(self, tesseract_file, xml_dir=None):
		# save the location of the original file
		self.tesseract_file = tesseract_file
		if not tesseract_file.endswith('.hocr'):
			raise Exception(tesseract_file+' is not of type .hocr')
		# save the locaiton where corrected files will be saved to
		if xml_dir is None:
			xml_dir = os.sep.join(tesseract_file.split(os.sep)[:-2]) + os.sep + settings.xml_dir
		if not os.path.isdir(xml_dir):
			os.mkdir(xml_dir)
		self.xml_file = xml_dir + os.sep + tesseract_file.split(os.sep)[-1][:-len('.hocr')] + '.xml'
		# make a root to build the xml for the corrected file
		self.root = ET.Element("root")
		# open the hocr file and read in the output from tesseract
		with open(tesseract_file, 'r') as input_file:
			data = ' '.join([line for line in input_file])
			soup = BeautifulSoup(data, "html.parser")
			tag_list = soup.find_all('span', {'class':'ocr_line'})
			self.lines = [Line(t, self.root) for t in tag_list]
		self.correct_lines = []

	def __str__(self):
		return '\n'.join([str(l) for l in self.lines])

	def find_correct(self, correct_bags=None):
		bag_of_lines = [str(l) for l in self.lines]
		for correct_filename in correct_bags:
			num_same = len(set(correct_bags[correct_filename]) & set(bag_of_lines))
			perc_same = float(num_same)/len(bag_of_lines)
			# may need to work on cuttoff
			if perc_same > .1:
				self.assign_correct_bag(correct_filename, correct_bags[correct_filename])
				return correct_filename, correct_bags[correct_filename]
		print str(self)
		for correct_filename in correct_bags:
			num_same = len(set(correct_bags[correct_filename]) & set(bag_of_lines))
			perc_same = float(num_same)/len(bag_of_lines)
			print perc_same
		raise Exception('Could not find file match for '+self.tesseract_file)

	def assign_correct_bag(self, correct_filename, correct_lines):
		self.root.set('filename', correct_filename)
		self.correct_lines = correct_lines

	def remove_line(self, line):
		self.lines.remove(line)
		self.root.remove(line.et)

	def percent_of_initial_correct(self):
		bag_of_lines = [str(l) for l in self.lines]
		# start by finding the exact matches
		# currently we expect there to be a lot of these. This might not hold up in the future
		# other methods may be needed
		line_assignments = [-1] * len(bag_of_lines)
		for i in range(len(bag_of_lines)):
			if bag_of_lines[i] in self.correct_lines:
				corrected_line_index = self.correct_lines.index(bag_of_lines[i])
				line_assignments[i] = corrected_line_index
		# find the minimum, maximum and std of currect lines
		# (we will use this to determine if incorrect lines should be included)
		totally_correct_lines = [self.lines[i] for i in range(len(self.lines)) if line_assignments[i] != -1]
		return float(len(totally_correct_lines))/len(self.lines)

	# This is the first half of the assign_lines function.
	# I made it into it's own function for testing purposes.
	def get_line_matches(self, testing=False):
		if len(self.correct_lines) == 0:
			raise RuntimeError('Need to assign correct lines to document')
		# pair each word with it's line
		word_pairings = []
		for i in range(len(self.correct_lines)):
			for w in self.correct_lines[i].split(' '):
				if len(w) > 0:
					word_pairings.append((w,i))
		word_counts = Counter([x[0] for x in word_pairings])
		unique_words = dict([x for x in word_pairings if word_counts[x[0]] == 1])
		# start by finding words which are exact matches and occur only once in the document
		# if there are at least two such words in a line and all found words correspond to the same 
		# line, match the two lines
		line_assignments = [-1] * len(self.lines)
		# keep track of the words you find for auditing the system
		words_found = {}
		for i in range(len(self.lines)):
			word_assignments = []
			wf_list = []
			for w in self.lines[i].children:
				word_text = w.text
				if word_text in unique_words:
					word_assignments.append(unique_words[word_text])
					wf_list.append(word_text)
			if len(word_assignments) > 1 and word_assignments.count(word_assignments[0]) == len(word_assignments):
				line_assignments[i] = word_assignments[0]
				words_found[i] = wf_list
		# find the minimum, maximum and std of currect lines
		# (we will use this to determine if incorrect lines should be included)
		matched_lines = [self.lines[i] for i in range(len(self.lines)) if line_assignments[i] != -1]
		if len(matched_lines) == 0:
			print self.tesseract_file
			print self.lines
			raise RuntimeError('No lines matched')
		# if we are testing this system return the words which were found too
		if testing:
			return matched_lines, line_assignments, words_found
		else:
			return matched_lines, line_assignments

	def assign_lines(self, testing=False):
		matched_lines, line_assignments = self.get_line_matches()
		right_points = [l.bbox.right for l in matched_lines]
		left_points = [l.bbox.left for l in matched_lines]
		Dimensions = namedtuple('Dimensions', ['min', 'max', 'std'])
		right_dimensions = Dimensions(min(right_points), max(right_points), reasonable_deviation(right_points, left_points))
		left_dimensions = Dimensions(min(left_points), max(left_points), reasonable_deviation(left_points, right_points))
		# make a list of the assignments to be carried out which can be looked at seperately by the tester
		final_assignment = []
		# fill in missing lines (for the moment assume no mistakes with the original matching step)
		for i, line_match_i in enumerate(line_assignments):
			if line_match_i != -1:
				final_assignment.append((i, line_match_i))
				continue
			# I need to do something to prevent highlights from being seen as part of the text
			# However just rejecting things which are abnormally sized doesn't work because titles will
			# be rejected.
			low_index, high_index = self.find_line_to_assign(line_assignments, i)
			distance = 1.0
			correct_line_index = None
			# look through candidates for the most likely match
			# make sure indexes stay within the bounds of self.correct_lines
			# you will need to add 1 to high_index so the loop will work when high_index == low_index
			for line_index in range(max(low_index, 0), min(high_index+1, len(self.correct_lines))):
				d = self.lines[i].levenshteinDistance(self.correct_lines[line_index])
				if d < distance:
					distance = d
					correct_line_index = line_index
			# if a good candidate couldn't be found, blank the line
			if correct_line_index is None:
				final_assignment.append((i, None))
				continue
			# less than 50% of the line needs to be changed
			# (this may be a substring so it can actually be quite far from the correct line)
			# while in general the distance for matches has been less than 10%, I have seen it rise above 20% for 
			# short lines with lots of numbers
			if distance < .6:
				final_assignment.append((i, correct_line_index))
			else:
				final_assignment.append((i, None))
		# if this is not a test carry out the assignments. Otherwise return the result
		if not testing:
			# make a list of lines to delete and delete them after assigning the rest of the lines
			# (so as not to change the indices)
			blank_lines = []
			for index_pair in final_assignment:
				if index_pair[1] is not None:
					self.lines[index_pair[0]].assign_matching(self.correct_lines[index_pair[1]])
				else:
					blank_lines.append(self.lines[i])
			# remove lines which were not matched
			for l in blank_lines:
				self.remove_line(l)
		else:
			conversion_fun = lambda p : (self.lines[p[0]], self.correct_lines[p[1]] if p[1] is not None else None)
			return [conversion_fun(p) for p in final_assignment]

	def find_line_to_assign(self, line_assignments, index, forward=True):
		iterator = 1 if forward else -1
		next_found_index = index+iterator
		while next_found_index < len(line_assignments) and next_found_index >= 0 and line_assignments[next_found_index] == -1:
			next_found_index += iterator
		if next_found_index >= 0 and next_found_index < len(self.lines):
			# range of indexes to check
			perfect_coverage_index = line_assignments[next_found_index] - (next_found_index-index)
			no_coverage_index = line_assignments[next_found_index] - iterator
			# put the higher number first to make them easier to assign
			if perfect_coverage_index > no_coverage_index:
				return no_coverage_index, perfect_coverage_index
			else:
				return perfect_coverage_index, no_coverage_index
		else:
			if forward:
				return self.find_line_to_assign(line_assignments, index, forward=False)
			else:
				print line_assignments
				print self.tesseract_file
				print self.correct_lines
				print str(self)
				print set([str(l) for l in self.lines]) & set(self.correct_lines)
				raise Exception('No totally correct lines found')

	def scale(self, right_shift, down_shift, multiple):
		for l in self.lines:
			l.scale(right_shift, down_shift, multiple)

	def save(self):
		tree = ET.ElementTree(self.root)
		tree.write(self.xml_file)

# If the standard deviation is too small, we shouldn't use it
def reasonable_deviation(list_of_numbers, second_list):
	min_val = min(list_of_numbers + second_list)
	max_val = max(list_of_numbers + second_list)
	return float(max_val - min_val)/4

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
	# some session ids from the pilot data
	all_sessions = get_session_names()

	t0 = time.time()
	for sess_name in all_sessions:
		sess = Session(sess_name)
		print sess_name
		find_percent_correct(sess)
		#cleanup(sess)
	t1 = time.time()
	print 'time taken', t1 - t0, 'seconds'
