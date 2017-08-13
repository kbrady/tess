import ocr_cleanup
# to write and read output
import csv
# to split by os seperator
import os
# to debug
import sys
# a few uses
from collections import Counter

def line_match_test(hocr_file, correct_filename):
	correct_bags = ocr_cleanup.get_correct_bags()
	doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
	doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
	matched_lines, line_assignments, words_found = doc.get_line_matches(testing=True)
	for hocr_index, correct_index in enumerate(line_assignments):
		hocr_text = str(doc.lines[hocr_index])
		correct_text = -1 if correct_index == -1 else correct_bags[correct_filename][correct_index]
		wf = words_found.get(hocr_index, [])
		print hocr_text
		print '\t', correct_text
		print '\t', wf

def line_assignment_test(hocr_file, correct_filename):
	correct_bags = ocr_cleanup.get_correct_bags()
	doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
	doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
	assignment = doc.assign_lines(testing=True)
	# check which lines are matched using the Levinstein Similarity
	# and which are matched on shared words
	matched_lines, line_assignments, words_found = doc.get_line_matches(testing=True)
	# save output to file
	stats_file = 'test-output' + os.sep + hocr_file.split(os.sep)[-1][:-len('.hocr')]+'.csv'
	with open(stats_file, 'w') as outfile:
		writer = csv.writer(outfile, delimiter=',', quotechar='"')
		writer.writerow(['Tesseract Line', 'Corrected Line', 'Matched Using Words', 'Line ID'])
		for pair in assignment:
			matched_on_words = 1 if pair[1] is not None and correct_bags[correct_filename].index(pair[1]) in line_assignments else 0
			writer.writerow(list(pair) + [matched_on_words, pair[0].id])

def line_similarity_test(hocr_file, correct_filename):
	correct_bags = ocr_cleanup.get_correct_bags()
	doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
	stats_file = 'test-output' + os.sep + hocr_file.split(os.sep)[-1][:-len('.hocr')]+'_sim.csv'
	with open(stats_file, 'w') as outfile:
		writer = csv.writer(outfile, delimiter=',', quotechar='"')
		writer.writerow(['line'] + correct_bags[correct_filename])
		for l in doc.lines:
			row = [str(l)]
			for correct_string in correct_bags[correct_filename]:
				row.append(l.levenshteinDistance(correct_string))
			writer.writerow(row)

def get_unique_words(correct_file):
	correct_bags = ocr_cleanup.get_correct_bags()
	correct_lines = correct_bags[correct_file]
	# pair each word with it's line
	word_pairings = []
	for i in range(len(correct_lines)):
		for w in correct_lines[i].split(' '):
			if len(w) > 0:
				word_pairings.append((w,i))
	word_counts = Counter([x[0] for x in word_pairings])
	unique_words = dict([x for x in word_pairings if word_counts[x[0]] == 1])
	for i in range(len(correct_lines)):
		ammended_line = []
		for w in correct_lines[i].split(' '):
			if w in unique_words:
				ammended_line.append(w)
		print ' '.join(ammended_line)

def get_lines(hocr_file):
	doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
	for l in doc.lines:
		print l

def compare_lines():
	corr = """
		1920: Women Get the Vote
		by Sam Roberts
		The 19th Amendment was ratified in 1920, after decades of campaigning by the women's suffrage
		movement.
		When John Adams and his fellow patriots were mulling independence from England in the spring of 1776, Abigail
		Adams famously urged her husband to "remember the ladies and be more generous and favorable to them than your
		ancestors." Otherwise, she warned, "we are determined to foment a rebellion, and will not hold ourselves bound by
		any laws in which we have no voice or representation."
		"""
	corr_list = [l.strip() for l in corr.split('\n')]
	hocr = """

		.- womens_3uf-rage_T_B.hzm|
		 
		1920: Women Get the Vote
		by Sam Roberts
		 
		The 19th Amendment was ratified in 1920, after decades of campaigning by the women's suffrage
		movement.
		 
		 
		When John Adams and his fellow patriots were mulling independence from England in the spring of 1776, Abigail
		Adams famously urged her husband to "remember the ladies and be more generous and favorable to them than your
		ancestors." Otherwise, she warned, "we are determined to foment a rebellion, and will not hold ourselves bound by
		"""
	for l in [l.strip() for l in hocr.split('\n')]:
		if l not in corr_list:
			print l

if __name__ == '__main__':
	#line_assignment_test('test-data/sidebar-open.hocr', 'digital_reading_1.txt')
	#line_assignment_test('test-data/dictionary-open.hocr', 'digital_reading_1.txt')
	#get_lines('test-data/03-26.6.hocr')
	#get_unique_words('digital_reading_1.txt')
	compare_lines()