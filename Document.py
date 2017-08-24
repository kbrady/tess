from Line import Line
# to save output from some functions
import csv
# to find files and parse paths correctly
import os
# to write corrected output to file
import xml.etree.cElementTree as ET
# to calculate statistics like stdev and median
import numpy as np
# to read hocr files and write xml files
from bs4 import BeautifulSoup
# to make word frequency vectors and store dimensions
from collections import Counter, namedtuple, defaultdict

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
			self.lines = [Line(t, self, self.root) for t in tag_list]
		self.correct_lines = []
		# create a function to detect lines which are close to the median height
		self.med_height = np.median([l.bbox.bottom - l.bbox.top for l in self.lines])
		height_epsilon = self.med_height * .1
		inside_bounds = lambda x, y, eps: x >= y - eps and x <= y + eps
		inside_height = lambda x, y, eps: inside_bounds(x.bbox.bottom - x.bbox.top, y, eps)
		self.close_to_median_height = lambda val : inside_height(val, self.med_height, height_epsilon)
		# calculate the median space width so it can be used in analysis
		self.calc_space_width()

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

	def calc_space_width(self):
		widths = []
		for l in self.lines:
			if not self.close_to_median_height(l):
				continue
			last_chunk = None
			for c in l.children:
				if last_chunk is not None:
					widths.append(c.bbox.left - last_chunk.bbox.right)
				last_chunk = c
		self.space_width = np.median(widths)

	# find the approximate width of each character.
	# This can be used to make educated decisions about gaps.
	# only run this function after running line assignment
	def calc_char_width(self, testing=True):
		# initialize by guessing everything is as wide as a space
		self.chr_widths = defaultdict(lambda:self.space_width)
		num_words = defaultdict(int)
		# find words which don't need correction
		perfect_words = []
		for l in self.lines:
			# only consider lines which are close to the median hight
			if not self.close_to_median_height(l):
				continue
			# find unique words in the corrected line
			correct_words = l.updated_line.split(' ')
			correct_word_counts = Counter(correct_words)
			# start by findind the anchors
			perfect_words += [c for c in l.children if correct_word_counts.get(c.text, 0) == 1]
		# go through chunks and update widths
		for chunk in perfect_words:
			word_width = chunk.bbox.right - chunk.bbox.left
			expected_width = sum([self.chr_widths[c] for c in chunk.text])
			for c in chunk.text:
				self.chr_widths[c] = self.chr_widths[c] * float(word_width)/expected_width
				num_words[c] += 1
		# when testing it is good to see the results as a csv
		if testing:
			with open('char_widths.csv', 'w') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				writer.writerow(['Char', 'Width', 'Num Sightings'])
				for c in self.chr_widths.keys():
					writer.writerow([c, self.chr_widths[c], num_words[c]])

	# This is far to simplistic and assumes all letters are about the same.
	# I need to re-write this to us a back propogation type update method.
	def get_char_width(self, testing=True):
		# find words which don't need correction
		perfect_words = []
		for l in self.lines:
			# only consider lines which are close to the median hight
			if not self.close_to_median_height(l):
				continue
			# find unique words in the corrected line
			correct_words = l.updated_line.split(' ')
			correct_word_counts = Counter(correct_words)
			# start by findind the anchors
			perfect_words += [c for c in l.children if correct_word_counts.get(c.text, 0) == 1]
		# gather the available data on each character
		character_data_points = defaultdict(list)
		for w in perfect_words:
			word_width = w.bbox.right - w.bbox.left
			word_length = len(w.text)
			fraciton = float(word_width)/word_length
			for c in w.text:
				character_data_points[c].append(fraciton)
		# calculate the average width for each character
		self.char_widths = {}
		for c in character_data_points:
			# need a couple datapoints to be reliable
			if len(character_data_points[c]) >= 5:
				self.char_widths[c] = np.mean(character_data_points[c])
		self.avg_char = np.mean(self.char_widths.values())
		# when testing it is good to see the results as a csv
		if testing:
			with open('char_widths.csv', 'w') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				writer.writerow(['Char', 'Width', 'Datapoints'])
				for c in self.char_widths:
					writer.writerow([c, self.char_widths[c], len(character_data_points[c])])

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
			# less than 60% of the line needs to be changed
			# (this may be a substring so it can actually be quite far from the correct line)
			# while in general the distance for matches has been less than 10%, I have seen it rise above 20% for 
			# short lines with lots of numbers
			if distance < .6:
				final_assignment.append((i, correct_line_index))
			else:
				final_assignment.append((i, None))
		# make a list of lines to delete and delete them after assigning the rest of the lines
		# (so as not to change the indices)
		blank_lines = []
		for index_pair in final_assignment:
			if index_pair[1] is not None:
				self.lines[index_pair[0]].assign_matching(self.correct_lines[index_pair[1]], testing=testing)
			else:
				blank_lines.append(self.lines[i])
		# remove lines which were not matched
		for l in blank_lines:
			if testing:
				l.assign_matching('', testing=testing)
			else:
				self.remove_line(l)
		if testing:
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