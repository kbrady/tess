import ocr_cleanup
# to write and read output
import csv
# to split by os seperator
import os
# to debug
import sys

def line_assignment_test(hocr_file, correct_filename):
	correct_bags = ocr_cleanup.get_correct_bags()
	doc = ocr_cleanup.Document(hocr_file, xml_dir='test-output')
	for l in doc.lines:
		print str(l)
	print "----"
	print "----"
	doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
	assignment = doc.assign_lines(testing=True)
	print '\n'.join([str(x) for x in assignment])
	print "----"
	stats_file = 'test-output' + os.sep + hocr_file.split(os.sep)[-1][:-len('.hocr')]+'.csv'
	with open(stats_file, 'w') as outfile:
		writer = csv.writer(outfile, delimiter=',', quotechar='"')
		writer.writerow(['Tesseract Line', 'Corrected Line'])
		for pair in assignment:
			writer.writerow(list(pair))
	for l in doc.lines:
		print str(l)

if __name__ == '__main__':
	line_assignment_test('test-data/sidebar-open.hocr', 'digital_reading_1.txt')