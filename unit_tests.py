# to make hocr tests
from bs4 import BeautifulSoup
# to run unit tests
import unittest
# to call in functions for testing
import ocr_cleanup
# to make tests not all standard
import random
# to build random strings
import string

class TestLevenshteinDistance(unittest.TestCase):

	def test_online_example(self):
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "c abba c", s2_edge_cost=0)*len("aba"), 1.0)
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "c abba c", s2_edge_cost=0.1)*len("aba"), 1.4)

	# At the moment this only considers ascii letters. We may want to change this in future.
	def test_skipping(self):
		for test_num in range(20):
			sub_string = ""
			for i in range(random.choice(range(20))):
				sub_string += random.choice(string.ascii_letters)
			larger_string = sub_string
			fluff_num = random.choice(range(10))
			for i in range(fluff_num):
				if random.choice([True, False]):
					larger_string = random.choice(string.ascii_letters) + larger_string
				else:
					larger_string += random.choice(string.ascii_letters)
			self.assertAlmostEqual(test_line_levenshteinDistance(sub_string, larger_string, s2_edge_cost=0.1)*len(sub_string), fluff_num*0.1)

def make_line_with_text(line_string):
	line_tag_text = """
	<span class='ocr_line' id='line_1_26' title="bbox 138 1288 268 1312; baseline 0 -6; x_size 30; x_descenders 6; x_ascenders 6">
	"""
	for word_text in line_string.split(' '):
		line_tag_text += "<span class='ocrx_word' id='word_1_206' title='bbox 138 1288 268 1312; x_wconf 89'>"
		line_tag_text += word_text
		line_tag_text += "</span>"
	line_tag_text += "</span>"
	line_tag = BeautifulSoup(line_tag_text, "html.parser")
	return ocr_cleanup.Line(line_tag.span)

def test_line_levenshteinDistance(line_string, correct_string, s2_edge_cost=.01, s2_mid_cost=1, s1_cost=1, sub_cost=1):
	my_line = make_line_with_text(line_string)
	return my_line.levenshteinDistance(correct_string, s2_edge_cost=s2_edge_cost, s2_mid_cost=s2_mid_cost, s1_cost=s1_cost, sub_cost=sub_cost)

if __name__ == '__main__':
	unittest.main()