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
global_id_dir = 'with-id-files'
highlights_dir = 'with-highlights'
# ranges for various parts of the stimuli
x_range = {
	'digital reading': [200, 1200],
	'form': [676, 1314],
	'typing': [0, 2880]
}
y_range = {
	'digital reading': [40, 860],
	'form': [143, 793],
	'typing': [0, 1800]
}

eye_tracking_mapped_csv_file = 'mapped_values.csv'

# a value for heatmaps
pixels_per_bin = 100

# possible file endings for screen recordings
movie_endings = ['.3g2', '.3gp', '.m2ts', '.mts', '.amv', '.asf', '.avi', '.drc', '.f4a', '.f4b', '.f4p', '.f4v', '.flv', '.gif', '.gifv', '.m2v', '.m4p', '.m4v', '.mkv', '.mng', '.mov', '.mp2', '.mp4', '.mpe', '.mpeg', '.mpg', '.mpv', '.mxf', '.nsv', '.ogg', '.ogv', '.qt', '.rm', '.rmvb', '.roq', '.svi', '.vob', '.webm', '.wmv', '.yuv']
movie_endings += [x.upper() for x in movie_endings]