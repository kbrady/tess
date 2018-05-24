from XML_META import XML_META

# An object to interpret words in hocr files
class Word(XML_META):
	def __init__(self, tag, parent, class_rules=None):
		super(self.__class__, self).__init__(tag, parent=parent, class_rules=class_rules)
		if len(self.text) > 0 and 'ocr_text' not in self.attrs:
			self.attrs['ocr_text'] = self.text

	def __repr__(self):
		return ''.join(filter(lambda x:ord(x) < 128, self.text))

	# I am making a word specific implementation of this so we can have fuzzy
	# matching for substrings (it is more likely that an OCR word contains two words than partial words)
	# this is the same as the line version except the long string is now the OCR one and the short
	# string is the correct one
	def levenshteinDistance(self, s1, s2_edge_cost=.01, s2_mid_cost=1, s1_cost=1, sub_cost=1):
		s2 = str(self)
		if len(s1.strip()) == 0:
			return len(s2)*s2_edge_cost
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
				if c1.lower() == c2.lower():
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
		return min(final_distances)

	# a function to calculate the similarity between this chunk and the text it is matched to
	# This takes into account both string similarity and the relative widths of the word and
	# the string it is matched to
	def match_difference(self, match_string):
		# calculate the string distance
		# we would rather have blank words than words which are only correct for 1 out of 20 letters
		# so I am using .8 for the edge cost
		string_distance = self.levenshteinDistance(match_string, s2_edge_cost=.8, s2_mid_cost=1, s1_cost=1, sub_cost=1)
		return string_distance

	def assign_matching(self, text, global_id=-1):
		if global_id == -1:
			self.text = text
		else:
			self.set_global_id(global_id)