# to time how long everything takes
import time
# to build the session and calculate scrolling
import video_to_frames
import initial_ocr
import ocr_cleanup
# to get the scrolling for each timepoint
import visualize_single_page
# to save scrolling data
import csv
import os

def calculate_line_values():
	# some session ids from the pilot data
	all_sessions = video_to_frames.get_session_names()
	# the bags of words for each correct document which will be used to correct the OCR
	correct_bags = ocr_cleanup.get_correct_bags()
	# a dictionary from each word to the documents it appears in
	word_to_doc = ocr_cleanup.make_matching_dictionary(correct_bags)

	for sess_name in all_sessions:
		print sess_name
		t0 = time.time()
		sess = video_to_frames.Session(sess_name)
		sess.break_into_10_second_chunks()
		sess.find_transitions()
		sess.calculate_metadata(save_to_file=True)
		sess.find_digital_reading_transitions()
		t1 = time.time()
		print t1 - t0, 'seconds to get frames'
		initial_ocr.make_ocr_ready_images(sess)
		initial_ocr.run_tesseract(sess)
		t2 = time.time()
		print t2 - t1, 'seconds to run initial ocr'
		ocr_cleanup.cleanup_session(sess, correct_bags, word_to_doc, stop_at_lines=True, alt_dir_name='line_matched')
		t3 = time.time()
		print t3 - t2, 'seconds to clean ocr'

if __name__ == '__main__':
	# the session names
	all_sessions = video_to_frames.get_session_names()

	for sess_name in all_sessions:
		print sess_name
		sess = video_to_frames.Session(sess_name)
		if not os.path.isfile(sess.dir_name + os.sep + 'scrolling.csv'):
			scroll_data, correct_doc = visualize_single_page.get_scroll(sess, xml_dir_extention='line_matched')
			scroll_data.sort(key=lambda x: x[0])
			csv_path = sess.dir_name + os.sep + 'scrolling.csv'
			with open(csv_path, 'w') as outputfile:
				writer = csv.writer(outputfile, delimiter=',', quotechar='"')
				writer.writerow(['time', 'top', 'bottom'])
				for dp in scroll_data:
					writer.writerow(dp)
		if not os.path.isfile(sess.dir_name + os.sep + 'scrolling.png'):
			visualize_single_page.plot_scroll(sess, xml_dir_extention='line_matched')