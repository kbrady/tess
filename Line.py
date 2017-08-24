# to inheret class definitions
from Word import Word
from Part import Part
from BBox import BBox
# to save output from some functions
import csv
# to write corrected output to file
import xml.etree.cElementTree as ET
# to make word frequency vectors and store dimensions
from collections import Counter, defaultdict

# An object to interpret lines in hocr files
class Line(Part):
	def __init__(self, tag, doc, et_parent=None):
		super(self.__class__, self).__init__(tag)
		self.updated_line = '' 
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, "line", bbox=str(self.bbox), id=self.id)
		else:
			self.et = ET.Element("line", bbox=str(self.bbox), id=self.id)
		self.children = [Word(sub_tag, self.et) for sub_tag in tag.find_all('span', {'class':'ocrx_word'})]
		self.word_hist = Counter([str(c) for c in self.children])
		self.letter_hist = Counter(str(self))
		self.doc = doc
	
	def __repr__(self):
		return ' '.join([str(word) for word in self.children])

	# I am making a line specific implementation of this so we can have fuzzy
	# matching for substrings (the whole line is sometimes not visible due to sidebar etc.)
	# 
	# The problem with this solution is that smaller lines may match better than correct lines
	# this is somewhat fixed by having a non-zero s2_edge_cost
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

	def assign_matching(self, string, testing=False):
		self.updated_line = string
		# we should keep track of line assignments seperately from word assignments
		# so we can audit the results
		self.et.set('updated_line', self.updated_line)
		# yet again we need the ability to run test runs
		if not testing:
			if len(string) > 0:
				assign(self.children, string.split(' '), complete_coverage=True)
			else:
				for word in self.children:
					word.assign_matching('')

	# estimate word breaks based on character distance
	def estimate_breaks(self, testing=False):
		# the line should have already been assigned to a correct string by this step
		# lines that didn't match anything get a blank updated line so we should return
		# an empty list
		if len(self.updated_line) == 0:
			return []
		# split up the correct string into word chunks
		correct_words = self.updated_line.split(' ')
		# estimate where the word breaks should be
		offset = self.bbox.left
		current_point = 0
		estimated_breaks = []
		# go through each word in the correct string and estimate where it
		# should start and stop based on character widths
		for word_text in correct_words:
			word_start = current_point
			word_end = word_start + sum([self.doc.chr_widths[c] for c in word_text])
			# scale lines which are not close to the median height
			# this assumes other sized fonts are about the same
			if not self.doc.close_to_median_height(self):
				scale = float(self.bbox.bottom - self.bbox.top)/self.doc.med_height
			else:
				scale = 1.0
			bbox_values = [word_start*scale + offset, self.bbox.top, word_end*scale + offset, self.bbox.bottom]
			info = ' '.join([str(int(x)) for x in bbox_values])
			estimated_breaks.append(BBox(info))
			current_point = word_end + self.doc.space_width
		# save results for auditing
		if testing:
			# Find words which have exact matches so their actual
			# positions can be compared to the computed location
			correct_word_counts = Counter(correct_words)
			ocr_words = [c.text for c in self.children]
			anchor_indexes = [i for i in range(len(ocr_words)) if correct_word_counts.get(ocr_words[i], 0) == 1]
			anchor_matchings = [correct_words.index(ocr_words[i]) for i in anchor_indexes]
			# append the output to a csv file
			# I am appending so we don't have a seperate file for each line
			with open('line_positions.csv', 'a') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				writer.writerow(['Line ID', 'Word', 'Left', 'Right', 'Actual Left', 'Actual Right', 'Left Offset', 'Right Offset'])
				for i in range(len(correct_words)):
					text = correct_words[i]
					left = estimated_breaks[i].left
					right = estimated_breaks[i].right
					if i in anchor_matchings:
						anchor_chunk = self.children[anchor_indexes[anchor_matchings.index(i)]]
						a_left = anchor_chunk.bbox.left
						a_right = anchor_chunk.bbox.right
					else:
						a_left = None
						a_right = None
					minus_or_none= lambda a, b: a-b if a is not None and b is not None else None
					writer.writerow([self.id, text, left, right, a_left, a_right, minus_or_none(a_left,left), minus_or_none(a_right,right)])
		return estimated_breaks

	# get the inital mapping
	def inital_mapping(self, testing=False):
		# the line should have already been assigned to a correct string by this step
		# lines that didn't match anything get a blank updated line so we should return
		# a meaningless dictionary
		if len(self.updated_line) == 0:
			return defaultdict(list)
		# start with an initial assignment based on estimated breaks and reject pairings which don't make sense
		estimated_breaks = self.estimate_breaks()
		correct_words = self.updated_line.split(' ')
		# itterate through the list and assign matchings
		ocr_index = 0
		pairing = defaultdict(list)
		for i in range(len(correct_words)):
			est_left = estimated_breaks[i].left
			est_right = estimated_breaks[i].right
			# iterate through children until we are in the right balpark
			while est_left >= self.children[ocr_index].bbox.right:
				ocr_index += 1
			current_word = self.children[ocr_index]
			# check if the overlap is good. If not go to the next word
			if ocr_index < len(self.children) - 1:
				if est_right > current_word.bbox.right:
					current_overlap = current_word.bbox.right - est_left
					next_overlap = est_right - self.children[ocr_index+1].bbox.left
					if next_overlap > current_overlap:
						ocr_index += 1
			pairing[ocr_index].append(i)
		# if we are testing, save the mapping for inspection
		if testing:
			with open('initital_mapping.csv', 'a') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				word_ids = [self.id]
				ocr_row = [self.id]
				mapping_row = [self.id]
				for ocr_index in range(len(self.children)):
					# make a space 
					if len(pairing[ocr_index]) == 0:
						word_ids.append(self.children[ocr_index].id)
						ocr_row.append(self.children[ocr_index].text)
						mapping_row.append('')
						continue
					for i in range(len(pairing[ocr_index])):
						word_ids.append(self.children[ocr_index].id)
						ocr_row.append(self.children[ocr_index].text)
						mapping_row.append(correct_words[pairing[ocr_index][i]])
				# write all three rows
				writer.writerow(word_ids)
				writer.writerow(ocr_row)
				writer.writerow(mapping_row)
		return pairing

	# better word assignment algorithm
	def assign_words(self):
		# start with an initial assignment based on estimated breaks and reject pairings which don't make sense
		correct_words = self.updated_line.split(' ')
		estimated_breaks = self.estimate_breaks()
		# find anchors and don't reasign them
		# find window of words which might correspond to each word we have

		correct_words = self.updated_line.split(' ')
		correct_word_counts = Counter(correct_words)
		ocr_words = [c.text for c in self.children]
		# start by findind the anchors
		anchor_indexes = [i for i in range(len(ocr_words)) if correct_word_counts.get(ocr_words[i], 0) == 1]
		anchor_matchings = [correct_words.index(ocr_words[i]) for i in anchor_indexes]
		# for the moment I am throwing an error here
		# practically I think this case most likely to occur on short lines where having no anchor wouldn't
		# be a big deal
		if len(anchor_indexes) == 0:
			raise Exception('There are no anchors in '+str(self))
		# next consider each un-anchored word chunk
		# keep track of the next and previous anchored word
		prev_anchor = None
		next_anchor = anchor_indexes[0]
		anchor_counter = 0
		for i in range(len(self.children)):
			# get the chunk
			chunk = self.children[i]
			# we do not need to considered anchored chunks
			if i in anchor_indexes:
				# but we do need to make assignments
				chunk.assign_matching(correct_words[anchor_matchings[anchor_counter]])
				# however we do need to know which anchor chunk came last and next
				prev_anchor = i
				anchor_counter += 1
				next_anchor = anchor_indexes[anchor_counter] if anchor_counter < len(anchor_indexes) else None
				continue
			# what are the candidate words?
			low_index = anchor_matchings[prev_anchor] + 1 if prev_anchor is not None else 0
			# we don't need to add a -1 because the range function takes care of that for us
			high_index = anchor_matchings[next_anchor] if next_anchor is not None else len(correct_words)
			candidate_indexes = range(low_index, high_index)
			# how far off are we from each candidate
			distances = [chunk.levenshteinDistance(correct_words[j]) for j in candidate_indexes]

			# how to make assignments without making mistakes?
			"""
			 NEED TO FILL IN
			"""
			# assign chunk
			# it might be wiser to do this later
			# will need to consider based on the evidece
			chunk.assign_matching(' '.join([correct_words[j] for j in found_words]))
			prev_anchor = i

	def scale(self, right_shift, down_shift, multiple):
		self.bbox.scale(right_shift, down_shift, multiple)
		self.et.set('bbox', str(self.bbox))
		for word in self.children:
			word.scale(right_shift, down_shift, multiple)
