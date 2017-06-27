# filepaths which point outside of this directory should not be in version control
from local_paths import *
# paths imported from local_paths.py
	# raw_dir_a
	# raw_dir_b
	# data_dir
frame_images_dir = 'frame-images'
metadata_file = 'metadata.json'
images_ready_for_ocr = 'resized-images'
hocr_dir = 'hocr-files'
xml_dir = 'xml-files'
digital_reading_x_range = [200, 1200]
digital_reading_y_range = [40, 860]
eye_tracking_word_csv_file = 'eye_tracking.csv'