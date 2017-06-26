# to read in files
import os
# to turn pictures from Piazza! into text which can be mapped to the text found in participant frame images
import initial_ocr
# to clean up tessaract reading of Piazza! image
import ocr_cleanup
# to read in xml files
import pair_screen_with_eyes
# to get the session info
from video_to_frames import Session
# to store values
from collections import defaultdict
# for making and reading images
from matplotlib import pyplot as plt
from PIL import Image

def images_to_xml():
	# Run tesseract on the website images
	image_dir = 'parts_for_viz'+os.sep+'resized-images'
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(image_dir):
		image_path = image_dir + os.sep + filename
		hocr_path = hocr_dir + os.sep + filename
		initial_ocr.run_tesseract_on_image(image_path, hocr_path)
	# Cleanup the tesseract output
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(hocr_dir):
		hocr_path = hocr_dir + os.sep + filename
		# turn off scaling since in this instance tesseract was run on the original image
		ocr_cleanup.cleanup_file(hocr_path, correct_bags=ocr_cleanup.get_correct_bags(), scale=False)

def get_viz_documents():
	viz_documents = {}
	xml_dir = 'parts_for_viz'+os.sep+'xml-files'
	for filename in os.listdir(xml_dir):
		xml_path = xml_dir + os.sep + filename
		viz_documents[filename] = pair_screen_with_eyes.Document(xml_path, None)
	return viz_documents

def get_mapping_function(frame_document, viz_document_dict):
	correct_doc = frame_document.correct_filepath
	# I should change this so it isn't hardcoded in the future
	viz_document = viz_document_dict['womens_suffrage_1_B.png.xml'] if '1' in correct_doc else viz_document_dict['womens_suffrage_2_A.png.xml']
	try:
		frame_top, viz_top = point_values(frame_document.lines[1], viz_document, top=True)
		frame_bottom, viz_bottom = point_values(frame_document.lines[-2], viz_document, top=False)
	except Exception as e:
		print 'Error raised while matching file '+frame_document.xml_filepath
		raise e
	x_fun = lambda x : (x-frame_top[0])*float(viz_bottom[0]-viz_top[0])/(frame_bottom[0]-frame_top[0]) + viz_top[0]
	y_fun = lambda y : (y-frame_top[1])*float(viz_bottom[1]-viz_top[1])/(frame_bottom[1]-frame_top[1]) + viz_top[1]
	return lambda x,y : (x_fun(x), y_fun(y))

# to get the change function from one to the other
def point_values(line_src, dst_document, top):
	dst_index = None
	for i in range(len(dst_document.lines)):
		if str(dst_document.lines[i]) == str(line_src):
			dst_index = i
			break
	if dst_index is None:
		raise Exception(str(line_src)+' has no match')
	x_src, y_src = get_x_and_y(line_src, top)
	x_dst, y_dst = get_x_and_y(dst_document.lines[dst_index], top)
	return (x_src, y_src), (x_dst, y_dst)

def get_x_and_y(line_val, top):
	x = line_val.bbox.left if top else line_val.bbox.right
	y = line_val.bbox.top if top else line_val.bbox.bottom
	return x, y

if __name__ == '__main__':
	# some session ids from the pilot data
	pilot_sessions = ['seventh_participant', 'fifth_participant', 'third_student_participant', 'first_student_participant_second_take', 'first_student_participant', 'Amanda', 'eighth_participant', 'sixth_participant', 'fourth-participant-second-version' , 'fourth_participant', 'second_student_participant']
	
	viz_documents = get_viz_documents()
	sess = Session(pilot_sessions[0])
	corpus = pair_screen_with_eyes.Corpus(sess)
	print corpus.documents[-5].xml_filepath
	print corpus.documents[-4].xml_filepath

