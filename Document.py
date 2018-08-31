# to inheret class definitions
from XML_META import XML_META
from Line import Line
from Word import Word
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
# to set the amount to scale by
import settings

class_rules = {'ocr_line': Line, 'ocrx_word': Word}

# An object to interpret hocr files
class Document(XML_META):
	def __init__(self, input_file, output_dir=None, time_in_seconds=None, calc_width=True):
		# save the location of the original file
		self.input_file = input_file
		if not input_file.endswith('.hocr'):
			raise Exception(input_file+' is not of type .hocr')
		# save the locaiton where corrected files will be saved to
		# if a value is passed for the xml_dir use that
		# this happens when we are testing and the tesseract_file is not part of a whole session
		if output_dir is None:
			output_dir = os.sep.join(input_file.split(os.sep)[:-2]) + os.sep + settings.xml_dir
		self.output_dir = output_dir
		# if we haven't built the xml directory already, make it
		if not os.path.isdir(output_dir):
			os.mkdir(output_dir)
		self.output_file = output_dir + os.sep + input_file.split(os.sep)[-1]
		# save the time in seconds of this document for later use
		self.time = time_in_seconds
		# open the hocr file and read in the output from tesseract
		with open(self.input_file, 'r') as input_file:
			data = ' '.join([line for line in input_file])
			soup = BeautifulSoup(data, "html.parser")
			# finally build using inheritance
			super(self.__class__, self).__init__(soup.find('html'), parent=None, class_rules=class_rules)
		# have a list of lines to refer to easily
		self.lines = self.find_all_lines()
		# if the path to the correct file was previously calucalated, use that
		self.correct_filepath = 'correct_text' + os.sep + self.attrs['filename'] if 'filename' in self.attrs else None
		# something to help calculate the correct lines if they haven't been calculated yet
		self.correct_lines = []
		# create a function to detect lines which are close to the median height
		self.med_height = np.median([l.title['bbox'].bottom - l.title['bbox'].top for l in self.lines])
		height_epsilon = self.med_height * .1
		inside_bounds = lambda x, y, eps: x >= y - eps and x <= y + eps
		inside_height = lambda x, y, eps: inside_bounds(x.height(), y, eps)
		self.close_to_median_height = lambda val : inside_height(val, self.med_height, height_epsilon)
		# calculate the median space width so it can be used in analysis
		if calc_width:
			self.calc_space_width()

	def __str__(self):
		return '\n'.join([str(l) for l in self.lines])

	# this function finds the most likely correct document for this OCR document
	# It does not make the assignment though
	def find_correct(self, word_to_doc, testing=False):
		bag_of_words = [w for l in self.lines for w in (str(l)).split(' ')]
		evidence = defaultdict(int)
		# count longer words as more important (these are less likely to be false positives)
		for w in bag_of_words:
			if len(w) < 2:
				continue
			for doc in word_to_doc[w]:
				evidence[doc] += np.log(len(w))
		if testing:
			document_sets = [word_to_doc[w] for w in bag_of_words]
			with open('document_counts.csv', 'w') as outputfile:
				writer = csv.writer(outputfile, delimiter=',', quotechar='"')
				abbrev_words = []
				abbrev_doc_sets = []
				for i in range(len(document_sets)):
					if len(document_sets[i]) > 0:
						abbrev_words.append(bag_of_words[i])
						abbrev_doc_sets.append(document_sets[i])
				writer.writerow(['Document', 'Count'] + abbrev_words)
				for filename, count in evidence.items():
					binary_fun = lambda i: 1 if filename in abbrev_doc_sets[i] else None
					binary_list = [binary_fun(i) for i in range(len(abbrev_doc_sets))]
					writer.writerow([filename, count] + binary_list)
		if len(evidence) == 0:
			print(self.output_file)
			raise Exception('None of the words found by OCR match a document')
		best_match, count = max(evidence.items(), key=lambda x: x[1])
		return best_match

	# This function assigns the correct document for fixing this document
	def assign_correct_bag(self, correct_filename, correct_lines):
		self.attrs['filename'] = correct_filename
		self.correct_lines = correct_lines

	# We will use the width of spaces as the default width for characters
	# This doesn't seem to be too far off.
	# A random document had a median space width of 6 pixels
	# The average character we collected information on was a little wider than 7 pixels
	def calc_space_width(self):
		widths = []
		for l in self.lines:
			if not self.close_to_median_height(l):
				continue
			last_chunk = None
			for c in l.children:
				if last_chunk is not None:
					widths.append(c.title['bbox'].left - last_chunk.title['bbox'].right)
				last_chunk = c
		self.space_width = np.median(widths)
		if np.isnan(self.space_width):
			print(self.input_file, 'widths', widths)
			self.space_width = 5.0

	# find the approximate width of each character.
	# This can be used to make educated decisions about gaps.
	# only run this function after running line assignment
	def calc_char_width(self, testing=False):
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
			word_width = chunk.title['bbox'].right - chunk.title['bbox'].left
			expected_width = sum([self.chr_widths[c] for c in chunk.text])
			for c in chunk.text:
				self.chr_widths[c] = self.chr_widths[c] * float(word_width)/expected_width
				num_words[c] += 1
		# when testing it is good to see the results as a csv
		if testing:
			filename = self.output_file[:-len('.hocr')] + '.csv'
			with open(filename, 'w') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				writer.writerow(['Char', 'Width', 'Num Sightings'])
				for c in self.chr_widths.keys():
					# divide by two since the image is blown up by two when it is resized
					writer.writerow([c, float(self.chr_widths[c]), num_words[c]])

	# This is far to simplistic and assumes all letters are about the same.
	# I need to re-write this to us a back propogation type update method.
	def get_char_width(self, testing=False):
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
	def get_line_matches(self, testing=False, correcting=True):
		correct_lines = self.correct_lines if correcting else [str(x) for x in self.prev_lines]
		if len(correct_lines) == 0:
			raise RuntimeError('Need to assign correct lines to document')
		# pair each word with it's line
		word_pairings = []
		for i in range(len(correct_lines)):
			for w in correct_lines[i].split(' '):
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
		# figure out which lines were matched
		matched_lines = [self.lines[i] for i in range(len(self.lines)) if line_assignments[i] != -1]
		if len(matched_lines) == 0:
			try:
				print(self.tesseract_file)
			except AttributeError as e:
				print(self.output_file)
			print(self.lines)
			print(correct_lines)
			raise RuntimeError('No lines matched')
		# if we are testing this system return the words which were found too
		if testing:
			return matched_lines, line_assignments, words_found
		else:
			return matched_lines, line_assignments

	def set_prev_lines(self, prev_lines):
		self.prev_lines = prev_lines

	# this function pairs each OCR line with a corrected string
	# (blank if nothing good is found)
	def assign_lines(self, testing=False, correcting = True):
		correct_lines = self.correct_lines if correcting else [str(x) for x in self.prev_lines]
		matched_lines, line_assignments = self.get_line_matches(correcting=correcting)
		# make a list of the assignments to be carried out which can be looked at seperately by the tester
		final_assignment = [-1] * len(self.lines)
		# fill in missing lines (for the moment assume no mistakes with the original matching step)
		for i, line_match_i in enumerate(line_assignments):
			if line_match_i != -1:
				final_assignment[i] = line_match_i
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
			for line_index in range(max(low_index, 0), min(high_index+1, len(correct_lines))):
				d = self.lines[i].levenshteinDistance(correct_lines[line_index])
				if d < distance:
					distance = d
					correct_line_index = line_index
			# if a good candidate couldn't be found, blank the line
			if correct_line_index is None:
				final_assignment[i] = None
				continue
			# less than 80% of the line needs to be changed
			# (this may be a substring so it can actually be quite far from the correct line)
			# while in general the distance for matches has been less than 10%, I have seen it rise above 20% for 
			# short lines with lots of numbers
			if distance < .6:
				final_assignment[i] = correct_line_index
			else:
				final_assignment[i] = None
		# clean up final assignment so correct line is assigned to more than one OCR line
		correct_line_assignment_count = defaultdict(list)
		for pair in enumerate(final_assignment):
			correct_line_assignment_count[pair[1]].append(pair[0])
		for correct_line_index in correct_line_assignment_count:
			if correct_line_index is None:
				continue
			if len(correct_line_assignment_count[correct_line_index]) > 1:
				# find the line which is closest to the assigned line
				best_index = correct_line_assignment_count[correct_line_index][0]
				best_distance = self.lines[best_index].levenshteinDistance(correct_lines[correct_line_index])
				for i in correct_line_assignment_count[correct_line_index][1:]:
					distance = self.lines[i].levenshteinDistance(correct_lines[correct_line_index])
					if distance < best_distance:
						best_distance = distance
						best_index = i
				# assign the correct line and void all others
				for i in correct_line_assignment_count[correct_line_index]:
					if i != best_index:
						final_assignment[i] = None
		# After consideration I think it is best not to delete blank lines
		# Deleteing these lines makes them harder to audit later
		for index_pair in enumerate(final_assignment):
			if index_pair[1] is not None:
				was_matched_in_first_step = True if self.lines[index_pair[0]] in matched_lines else False
				global_id = -1 if correcting else self.prev_lines[index_pair[1]].global_id
				self.lines[index_pair[0]].assign_matching(correct_lines[index_pair[1]], was_matched_in_first_step, global_id)
			else:
				global_id = -1 if correcting else None
				self.lines[index_pair[0]].assign_matching('', False, global_id)
		# if we are testing save the output to a file in the xml directory
		if testing:
			with open(self.output_dir + os.sep + 'line_assignment.csv', 'w') as outputfile:
				writer = csv.writer(outputfile, delimiter=',', quotechar='"')
				for pair in enumerate(final_assignment):
					writer.writerow([self.lines[pair[0]].id])
					writer.writerow([str(self.lines[pair[0]])])
					if pair[1] is None:
						writer.writerow([])
					else:
						writer.writerow([correct_lines[pair[1]]])

	# this function finds the window of assigned lines that this one appears in
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
				print(line_assignments)
				print(self.tesseract_file)
				print(self.correct_lines)
				print(str(self))
				print(set([str(l) for l in self.lines]) & set(self.correct_lines))
				raise Exception('No totally correct lines found')

	# function to make all corrections 
	def fix(self, right_shift=None, down_shift=None, stop_at_lines=False):
		self.assign_lines()
		if not stop_at_lines:
			self.calc_char_width()
			for l in self.lines:
				pairing = l.find_pairing()
				l.assign_words(pairing)
		if right_shift is not None:
			self.scale(right_shift, down_shift, 0.5)

	def scale(self, right_shift, down_shift, multiple):
		for l in self.lines:
			l.scale(right_shift, down_shift, multiple)

	def pair_to_prev_doc(self, prev_doc, save=True):
		this_doc_words = [w for l in self.lines for w in l.children]
		if prev_doc is None:
			for w in this_doc_words:
				w.set_global_id(w.id)
			if save:
				self.save()
			return
		prev_doc_words = [w for l in self.lines for w in l.children]
		mapping_to_prev = defaultdict(list)
		for w1 in this_doc_words:
			for w2 in this_doc_words:
				if w1.text == w2.text:
					mapping_to_prev[w1].append(w2)

	def save(self, alt_dir_name=None, use_same_overall_path=True):
		if alt_dir_name is not None:
			if use_same_overall_path:
				sess_dir = os.sep.join(self.output_dir.split(os.sep)[:-1])
				dir_name = sess_dir + os.sep + alt_dir_name
			else:
				dir_name = alt_dir_name
			if not os.path.isdir(dir_name):
				os.mkdir(dir_name)
			filepath = dir_name + os.sep + self.output_file.split(os.sep)[-1]
		else:
			filepath = self.output_file
		super(self.__class__, self).save(filepath)

	def get_word_distance(self, row):
		list_of_line_strings = [str(l) for l in self.lines]
		x, y = get_x_y(row)
		list_of_distances = []
		with open(self.correct_filepath, 'r') as word_file:
			for line in word_file:
				line = line.strip()
				if x == -1 or y == -1 or line not in list_of_line_strings:
					list_of_distances += [None] * len(line.split(' '))
					continue
				line_index = list_of_line_strings.index(line)
				list_of_distances += self.lines[line_index].get_distances(x,y)
		return list_of_distances

	def get_words(self):
		with open(self.correct_filepath, 'r') as word_file:
			return [word for line in word_file for word in line.strip().split(' ')]
