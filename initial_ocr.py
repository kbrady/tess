# to find files and run tesseract
import os
# to look in the right places
import settings
# to get the session info and find parts of an image
import video_to_frames
# to resize images and save them
from scipy import ndimage, misc
# to time the process
import time
# to run subprocesses without dealing with spaces etc. by myself
import subprocess

def make_ocr_ready_images(sess):
	digital_reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
	for reading_interval in digital_reading_times:
		for image_time in reading_interval['transitions']:
			filename = video_to_frames.time_to_filename(image_time)
			full_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + filename
			pic = video_to_frames.get_part_of_picture(full_path, x_range=settings.digital_reading_x_range, y_range=settings.digital_reading_y_range)
			bigger_pic = ndimage.zoom(pic, (2, 2, 1), order=0)
			dir_for_bigger_images = sess.dir_name + os.sep + settings.images_ready_for_ocr
			if not os.path.isdir(dir_for_bigger_images):
				os.mkdir(dir_for_bigger_images)
			full_path_for_new_image = dir_for_bigger_images + os.sep + filename
			misc.imsave(full_path_for_new_image, bigger_pic)

def run_tesseract(sess):
	digital_reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
	for reading_interval in digital_reading_times:
		for image_time in reading_interval['transitions']:
			filename = video_to_frames.time_to_filename(image_time)
			image_dir = sess.dir_name + os.sep + settings.images_ready_for_ocr
			image_path = image_dir + os.sep + filename
			hocr_dir = sess.dir_name + os.sep + settings.hocr_dir
			if not os.path.isdir(hocr_dir):
				os.mkdir(hocr_dir)
			hocr_path = hocr_dir + os.sep + '.'.join(filename.split('.')[:-1])
			run_tesseract_on_image(image_path, hocr_path)

def run_tesseract_on_image(image_path, hocr_path):
	command = ['tesseract', image_path, hocr_path, '-l', 'eng', 'hocr']
	subprocess.call(command)

if __name__ == '__main__':
	# some session ids from the pilot data
	all_sessions = video_to_frames.get_session_names()

	t0 = time.time()
	for sess_name in all_sessions:
		sess = video_to_frames.Session(sess_name)
		make_ocr_ready_images(sess)
		run_tesseract(sess)
	t1 = time.time()
	print 'time taken', t1 - t0

