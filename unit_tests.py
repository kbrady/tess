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
# to see what the failed arguements are in a random test
import logging
# for debugging
import sys

class TestLevenshteinDistance(unittest.TestCase):

	def test_obvious_cases(self):
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "aba", s2_edge_cost=0.1), 0.0)
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "abba", s2_edge_cost=0.1)*len("aba"), 1.0)
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "abab", s2_edge_cost=0.1)*len("aba"), 0.1)

	def test_online_example(self):
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "c abba c", s2_edge_cost=0)*len("aba"), 1.0)
		self.assertAlmostEqual(test_line_levenshteinDistance("aba", "c abba c", s2_edge_cost=0.1)*len("aba"), 1.4)

	# At the moment this only considers ascii letters. We may want to change this in future.
	def test_skipping(self):
		log= logging.getLogger( "TestLevenshteinDistance.test_skipping" )
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
			# log this stuff in case the test fails
			log.debug( "sub_string= %s", sub_string )
			log.debug( "larger_string= %s", larger_string )
			if len(sub_string) > 0:
				self.assertAlmostEqual(test_line_levenshteinDistance(sub_string, larger_string, s2_edge_cost=0.1)*len(sub_string), fluff_num*0.1)
			else:
				self.assertAlmostEqual(test_line_levenshteinDistance(sub_string, larger_string, s2_edge_cost=0.1), 1.0)

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

class TestLineAssignment(unittest.TestCase):

	def test_line_assignment_test(self):
		hocr_file = 'test-data/sidebar-open.hocr'
		correct_filename = 'digital_reading_1.txt'
		correct_bags = ocr_cleanup.get_correct_bags()
		doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
		doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
		assignment = doc.assign_lines(testing=True)
		# this is how the matching should be
		correct_matching = {
			'line_1_18':'"Womanifesto"',
			'line_1_22':"a demand for equal voting rights, also known as universal suffrage. \"I saw clearly,\" Stanton later recalled, \"that the",
			'line_1_27':"alcohol), women often enlisted in the fight for voting rights too. Women suffrage organizations even harnessed the",
			'line_1_5':"be denied or abridged by the United States or by any State on account of sex.\" It took effect after a dramatic",
			'line_1_9':"could rarely vote. (As far back as 1776, New Jersey allowed women property owners to vote, but rescinded that right",
			'line_1_15':"Did you know: Elizabeth Cady Stanton was the first women to run for congress-back in 1866.",
			'line_1_12':"ELIZABETH CADY STANTON SUSAN B. ANTHONY",
			'line_1_29':"image of their campaign orchestrated by anti-suffrage opponents.",
			'line_1_20':"organized by 32-year-old Elizabeth Cady Stanton and other advocates. Stanton had drafted a \"Womanifesto\"",
			'line_1_21':"patterned on the Declaration of Independence, but the one resolution that shocked even some of her supporters was",
			'line_1_23':"power to make the laws was the right through which all other rights could be secured.\"",
			'line_1_28':"propaganda value of materials such as picture postcards as a visual corrective to what they saw as a misleading",
			'line_1_7':"ratification battle in Tennessee in which a 24-year-old legislator cast the deciding vote.",
			'line_1_24':"Stanton was joined in her campaign by Susan B. Anthony, Sojourner Truth, Lucretia Mott, and other crusaders who",
			'line_1_8':"The amendment was a long time coming. At various times, women could run for public office in some places, but",
			'line_1_19':"The campaign for women's rights began in earnest in 1848 at a Women's Rights convention in Seneca Falls, N.Y.,",
			'line_1_10':"three decades later.)",
			'line_1_26':"violence. Already active in the antislavery movement and temperance campaigns (which urged abstinence from",
			'line_1_25':"would become icons of the women's movement. Some were militant. Many were met with verbal abuse and even"}
		for pair in assignment:
			if pair[0].id in correct_matching:
				self.assertEqual(pair[1], correct_matching[pair[0].id])
			else:
				self.assertEqual(pair[1], None)

if __name__ == '__main__':
	logging.basicConfig( stream=sys.stderr )
	#logging.getLogger( "TestLevenshteinDistance.test_skipping" ).setLevel( logging.DEBUG )
	unittest.main()