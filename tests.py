# import modules to test
import ocr_cleanup
import initial_ocr
from Document import Document
# to write and read output
import csv
# to split by os seperator
import os
# to debug
import sys
# a few uses
from collections import Counter
# to get standard directory names
import settings

# test cases

def four_frames_test():
	# make directories
	original_pic_dir = 'tests/four-frames/original-pictures'
	dir_for_bigger_images = 'tests/four-frames' + os.sep + settings.images_ready_for_ocr
	if not os.path.isdir(dir_for_bigger_images):
		os.mkdir(dir_for_bigger_images)
	dir_for_hocr = 'tests/four-frames' + os.sep + settings.hocr_dir
	if not os.path.isdir(dir_for_hocr):
		os.mkdir(dir_for_hocr)
	dir_for_xml = 'tests/four-frames' + os.sep + settings.xml_dir
	if not os.path.isdir(dir_for_xml):
		os.mkdir(dir_for_xml)
	# make initial run through the images
	for filename in os.listdir(original_pic_dir):
		# resize
		full_path = original_pic_dir + os.sep + filename
		full_path_for_new_image = dir_for_bigger_images + os.sep + filename
		initial_ocr.resize_image(full_path, full_path_for_new_image, redo=True, part='digital reading')
		# run tesseract
		full_path_for_hocr = dir_for_hocr + os.sep + filename
		initial_ocr.run_tesseract_on_image(full_path_for_new_image, full_path_for_hocr, redo=True)
	# make corrections
	correct_bags = ocr_cleanup.get_correct_bags()
	word_to_doc = ocr_cleanup.make_matching_dictionary(correct_bags)
	ocr_cleanup.cleanup_hocr_files(dir_for_hocr, dir_for_xml, correct_bags, word_to_doc)
	# find differences
	for filename in os.listdir(dir_for_xml):
		full_path = dir_for_xml + os.sep + filename
		doc = Document(full_path)
		lines = [str(l).strip() for l in doc.lines if len(str(l).strip()) > 0]
		filename_with_txt_ending = filename[:-len('png.hocr')] + 'txt'
		path_to_correct_lines_file = 'tests/four-frames' + os.sep + 'limited-correct-output-text' + os.sep + filename_with_txt_ending
		with open(path_to_correct_lines_file, 'r') as infile:
			correct_lines = [line.strip() for line in infile]
		if len(lines) != len(correct_lines):
			raise Exception('lines has length {0} but correct_lines has length {1} for {2}'.format(len(lines), len(correct_lines), filename))
		for i in range(len(lines)):
			if lines[i] != correct_lines[i]:
				raise Exception('lines[{0}] has value\n{1}\n but correct_lines[{0}] has value\n{2}\n for {3}'.format(i, lines[i], correct_lines[i], filename))
	print('Four frames test passed')

if __name__ == '__main__':
	four_frames_test()
