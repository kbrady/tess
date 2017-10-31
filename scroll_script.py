# to time how long everything takes
import time
# to build the session and calculate scrolling
import video_to_frames
import initial_ocr
import ocr_cleanup

if __name__ == '__main__':
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
		print t2 - t1, 'seconds to clean ocr'