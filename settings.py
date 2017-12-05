# filepaths which point outside of this directory should not be in version control
from local_paths import *
# paths imported from local_paths.py
	# raw_dirs
	# data_dir
frame_images_dir = 'frame-images'
transition_images = 'transition-images'
metadata_file = 'metadata.json'
images_ready_for_ocr = 'resized-images'
hocr_dir = 'hocr-files'
xml_dir = 'xml-files'
# ranges for various parts of the stimuli
x_range = {
	'digital reading': [200, 1200],
	'form': [676, 1314]
}
y_range = {
	'digital reading': [40, 860],
	'form': [143, 793]
}
eye_tracking_word_csv_file = 'eye_tracking.csv'
eye_tracking_mapped_csv_file = 'mapped_values.csv'
# a value for heatmaps
pixels_per_bin = 100