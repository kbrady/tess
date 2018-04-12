# to inheret class definitions
from Word import Word
from Part import Part
from BBox import BBox
# to save output from some functions
import csv
# to make word frequency vectors and store dimensions
from collections import Counter, defaultdict

global_id_counter = 0

# An object to interpret lines in hocr files
class Line(Part):
	def __init__(self, tag, doc, et_parent=None):
		super(self.__class__, self).__init__(tag)
		if tag.has_attr('title'):
			self.init_to_fix(tag, doc, et_parent)
		else:
			self.init_to_read(tag, doc, et_parent)
		
	def init_to_read(self, tag, doc, et_parent=None):
		try:
			self.updated_line = tag['updated_line']
		except KeyError as e:
			self.updated_line = None
		# make an element tree object to save everything as xml
		self.set_et(et_parent, 'line')
		# import attrbutes
		self.attrs = tag.attrs
		# set attributes in saved version
		for k in self.attrs:
			self.et.set(k, self.attrs[k])
		self.children = [Word(sub_tag, self, self.et) for sub_tag in tag.find_all('word')]
		self.doc = doc

	def init_to_fix(self, tag, doc, et_parent=None):
		self.updated_line = ''
		# make an element tree object to save everything as xml
		self.set_et(et_parent, 'line')
		# populate children
		self.children = [Word(sub_tag, self, self.et) for sub_tag in tag.find_all('span', {'class':'ocrx_word'})]
		# we need a pointer to the document to use character widths
		# to make the initial mapping
		self.doc = doc
	
	def __repr__(self):
		return ' '.join([str(word) for word in self.children])

	# a function used by pair_with_eyes
	def get_distances(self, x, y):
		output = []
		for word in self.children:
			distance = word.get_distance(x,y)
			# if more than one 'word' got assigned to the same box then we need to double count that distance
			output += [distance] * len(str(word).split(' '))
		return output

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

	def assign_matching(self, string, first_step=False, global_id=-1):
		global global_id_counter
		if global_id == -1:
			self.update_with_correct(self, string, first_step)
		else:
			if global_id is None:
				self.set_global_id(str(global_id_counter))
				global_id_counter += 1
			else:
				self.set_global_id(global_id)

	def set_global_id(self, global_id):
		self.global_id = global_id
		self.et.set('global_id', global_id)

	def update_with_correct(self, string, first_step=False):
		self.updated_line = string
		# we should keep track of line assignments seperately from word assignments
		# so we can audit the results
		self.et.set('updated_line', self.updated_line)
		self.et.set('in_first_step', str(first_step))

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
	def initial_mapping(self, testing=False):
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
			while ocr_index < len(self.children) and est_left >= self.children[ocr_index].bbox.right:
				ocr_index += 1
			# if we have gotten to the end of the line there is nothing more to be done
			if ocr_index >= len(self.children):
				break
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
			with open('initial_mapping.csv', 'a') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				word_ids = [self.id]
				ocr_row = [self.id]
				mapping_row = [self.id]
				for ocr_index in range(len(self.children)):
					# record the pairing
					word_ids.append(self.children[ocr_index].id)
					ocr_row.append(self.children[ocr_index].text)
					mapping_row.append(' '.join([correct_words[i] for i in pairing[ocr_index]]))
				# write all three rows
				writer.writerow(word_ids)
				writer.writerow(ocr_row)
				writer.writerow(mapping_row)
		return pairing

	def difference_function(self, chunk_string_assignments):
		difference = 0
		for pair in chunk_string_assignments:
			difference += pair[0].match_difference(pair[1])
		return difference

	def push_out(self, chunk_index, current_pairing, split_1=None, split_2=None):
		# I don't do a complete search to find if the splits are valid,
		# but this might be a hard one to catch
		if split_2 < split_1:
			raise Exception('split_1 < split_2 but '+str(split_1)+' > '+str(split_2))
		# get the correct words
		correct_words = self.updated_line.split(' ')
		# make a function to pull out word strings
		indexes_to_words = lambda ocr_index : [correct_words[i] for i in current_pairing[ocr_index]]
		# get the words currently assigned to the current chunk
		current_words = indexes_to_words(chunk_index)
		split_1 = 0 if split_1 is None else split_1
		split_2 = len(current_words) if split_2 is None else split_2
		# calculate the string for each chunk
		chunk_string_assignments = [(self.children[chunk_index], ' '.join(current_words[split_1:split_2]))]
		if chunk_index > 0:
			prev_string = ' '.join(indexes_to_words(chunk_index - 1) + current_words[:split_1])
			chunk_string_assignments.append((self.children[chunk_index - 1], prev_string))
		if chunk_index + 1 < len(self.children):
			next_string = ' '.join(current_words[split_2:] + indexes_to_words(chunk_index + 1))
			chunk_string_assignments.append((self.children[chunk_index + 1], next_string))
		return self.difference_function(chunk_string_assignments)

	# in this case we need to report the distance before and the distance after
	# since the difference for the chunk being pulled from must also be considered
	# I confused left and right and should fix this...
	def pull_in(self, chunk_index, current_pairing, from_left=True):
		# if the line is empty don't bother
		if len(self.updated_line) == 0:
			return 0, 0, None, None
		# get the correct words
		correct_words = self.updated_line.split(' ')
		# make a function to pull out word strings
		indexes_to_words = lambda ocr_index : [correct_words[i] for i in current_pairing[ocr_index]]
		# find the next word
		next_ocr_index = None
		# if we are coming from the right, only consider chunks with lower indexes
		# from the left only consider chunks with higher indexes
		ocr_index_list = range(chunk_index-1,-1,-1) if from_left else range(chunk_index+1, len(self.children))
		# find the first chunk which is not empty
		for index_to_check in ocr_index_list:
			if len(current_pairing[index_to_check]) > 0:
				next_ocr_index = index_to_check
				break
		# if there is no word in a chunk after or before this one,
		# try pulling off screen words from correct_words
		if next_ocr_index is None:
			values_in_pairing = [v for l in current_pairing.values() for v in l]
			# if there is nothing to the left of this word, the first off screen word will
			# have a smaller index than those on screen
			if from_left:
				if len(values_in_pairing) == 0:
					next_correct_index = len(correct_words) - 1
				else:
					next_correct_index = min(values_in_pairing) - 1
			# if there is nothing to the right of this word, the first off screen word will
			# have a larger index than those on screen
			else:
				if len(values_in_pairing) == 0:
					next_correct_index = 0
				else:
					next_correct_index = max(values_in_pairing) + 1
			# if there is nothing off screen, return None
			if next_correct_index >= len(correct_words) or next_correct_index < 0:
				return 0, 0, None, None
			# if there is something off screen, consider pulling it on
			word_to_try = correct_words[next_correct_index]
			difference_before = self.difference_function([(self.children[chunk_index], '')])
			difference_after = self.difference_function([(self.children[chunk_index], word_to_try)])
			return difference_before, difference_after, next_correct_index, None
		else:
			# have something to compare to
			difference_before = self.difference_function([(self.children[chunk_index], '')])
			next_string = ' '.join(indexes_to_words(next_ocr_index))
			difference_before += self.difference_function([(self.children[next_ocr_index], next_string)])
			# measure in the case where we change something
			if from_left:
				next_correct_index = current_pairing[next_ocr_index][-1]
			else:
				next_correct_index = current_pairing[next_ocr_index][0]
			word_to_try = correct_words[next_correct_index]
			next_string = ' '.join([correct_words[i] for i in current_pairing[next_ocr_index][1:]])
			chunk_string_assignments = [(self.children[chunk_index], word_to_try)]
			chunk_string_assignments.append((self.children[next_ocr_index], next_string))
			difference_after = self.difference_function(chunk_string_assignments)
			return difference_before, difference_after, next_correct_index, next_ocr_index

	# better word assignment algorithm
	def fix_pairing(self, initial_pairing, testing=False):
		# start with an initial assignment based on estimated breaks
		# and reject pairings which don't make sense
		pairing = initial_pairing
		# We make changes by "shoving" the inital pairing around.
		# In this case repeatedly make new splits and try to find a stable solution
		change = True
		iterations = 0
		# currently we are falling into loops. Need to think of way to fix
		while change and iterations < 20:
			iterations += 1
			change = False
			# the initial estimate tends to favor the left side so we favor the right side when fixing
			# this is do to the growing error term for the total character width estimate
			for ocr_index in range(len(self.children)-1,-1,-1):
				# if the chunk is empty, consider pulling words in
				if len(pairing[ocr_index]) == 0:
					best_word_index = None
					pulled_from = None
					right_before, right_after, word_candidate, ocr_candidate = self.pull_in(ocr_index, pairing, False)
					if right_before > right_after:
						best_word_index = word_candidate
						pulled_from = ocr_candidate
					left_before, left_after, word_candidate, ocr_candidate = self.pull_in(ocr_index, pairing, True)
					if left_before > left_after and left_before - left_after > right_before - right_after:
						best_word_index = word_candidate
						pulled_from = ocr_candidate
					# if either pull successfully found a better position update the pairing
					if best_word_index is not None:
						pairing[ocr_index] = [best_word_index]
						if pulled_from is not None:
							if ocr_index < pulled_from:
								pairing[pulled_from] = pairing[pulled_from][1:]
							else:
								pairing[pulled_from] = pairing[pulled_from][:-1]
						change = True
				# otherwise try to push words out or sideways
				else:
					# we can put two paritions in the current chunk's assignment to try and make something better
					# initialize the best split
					best_split = (0, len(pairing[ocr_index]))
					best_difference = self.push_out(ocr_index, pairing)
					for split_1 in range(len(pairing[ocr_index])+1):
						for split_2 in range(split_1,len(pairing[ocr_index])+1):
							difference = self.push_out(ocr_index, pairing, split_1, split_2)
							# if we have found a better split record it and do an update at the end
							if difference < best_difference:
								best_difference = difference
								best_split = (split_1, split_2)
					# if we found a better split make the update
					if best_split != (0, len(pairing[ocr_index])):
						new_prev = pairing[ocr_index - 1] + pairing[ocr_index][:best_split[0]]
						new_next = pairing[ocr_index][best_split[1]:] + pairing[ocr_index + 1]
						new_current = pairing[ocr_index][best_split[0]:best_split[1]]
						if ocr_index > 0:
							pairing[ocr_index - 1] = new_prev
						if ocr_index + 1 < len(self.children):
							pairing[ocr_index + 1] = new_next
						pairing[ocr_index] = new_current
						change = True
			# if we are testing, save the mapping for inspection
			if testing:
				# get the correct words (we only need these in the test case)
				correct_words = self.updated_line.split(' ')
				with open('fixed_mapping.csv', 'a') as output_file:
					writer = csv.writer(output_file, delimiter=',', quotechar='"')
					word_ids = [self.id]
					ocr_row = [self.id]
					mapping_row = [self.id]
					for ocr_index in range(len(self.children)):
						# record the pairing
						word_ids.append(self.children[ocr_index].id)
						ocr_row.append(self.children[ocr_index].text)
						mapping_row.append(' '.join([correct_words[i] for i in pairing[ocr_index]]))
					# write all three rows
					writer.writerow([iterations])
					writer.writerow(word_ids)
					writer.writerow(ocr_row)
					writer.writerow(mapping_row)
		return pairing

	def get_pairing_difference(self, pairing):
		# get the correct words
		correct_words = self.updated_line.split(' ')
		# make a function to pull out word strings
		ocr_index_to_string = lambda ocr_index : ' '.join([correct_words[i] for i in pairing[ocr_index]])
		# make a zipped list of keys and strings
		chunk_string_assignments = [(self.children[i], ocr_index_to_string(i)) for i in range(len(self.children))]
		return self.difference_function(chunk_string_assignments)

	# try moving everything in a pairing to the side to see if it leads to better hill climbing
	def shove_to_side(self, pairing, offset):
		new_pairing = defaultdict(list)
		for key in pairing:
			offset_key = key + offset
			if offset_key >= 0 and offset_key < self.children:
				new_pairing[offset_key] = pairing[key]
		return new_pairing

	# this function tries sliding the initial mapping over to see if hill climbing works better from
	# different starting points
	def find_pairing(self, testing=False):
		initial_pairing = self.initial_mapping()
		pairing = self.shove_to_side(initial_pairing, 0)
		pairing = self.fix_pairing(pairing)
		best_difference = self.get_pairing_difference(pairing)
		best_offset = 0
		# find out if we would get something better if we started with a different initial state
		for offset in [-6, -4, -2, 2, 4, 6]:
			offset_pairing = self.shove_to_side(initial_pairing, offset)
			offset_pairing = self.fix_pairing(offset_pairing)
			difference = self.get_pairing_difference(offset_pairing)
			# if a pairing which started with an offset is better
			# save it
			if difference < best_difference:
				best_difference = difference
				best_offset = offset
				pairing = offset_pairing
		self.et.set('offset', str(best_offset))
		# if we are testing, save the mapping for inspection
		if testing:
			# get the correct words (we only need these in the test case)
			correct_words = self.updated_line.split(' ')
			with open('final_mapping.csv', 'a') as output_file:
				writer = csv.writer(output_file, delimiter=',', quotechar='"')
				word_ids = [self.id]
				ocr_row = [self.id]
				mapping_row = [self.id]
				for ocr_index in range(len(self.children)):
					# record the pairing
					word_ids.append(self.children[ocr_index].id)
					ocr_row.append(self.children[ocr_index].text)
					mapping_row.append(' '.join([correct_words[i] for i in pairing[ocr_index]]))
				# write all three rows
				writer.writerow([best_offset])
				writer.writerow(word_ids)
				writer.writerow(ocr_row)
				writer.writerow(mapping_row)
		return pairing

	# assign corrected string values to each OCR chunk
	# (none of the previous functions do this)
	def assign_words(self, pairing):
		# get the correct words to assign to children
		correct_words = self.updated_line.split(' ')
		for ocr_index in range(len(self.children)):
			corrected_word_text = ' '.join([correct_words[i] for i in pairing[ocr_index]])
			self.children[ocr_index].assign_matching(corrected_word_text)

	# There are seperate scale functions for lines and words since lines must also
	# scale children
	def scale(self, right_shift, down_shift, multiple):
		self.bbox.scale(right_shift, down_shift, multiple)
		for word in self.children:
			word.scale(right_shift, down_shift, multiple)
