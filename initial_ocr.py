# to find files and run tesseract
import os
# to look in the right places
import settings
# to get the session info and find parts of an image
from video_to_frames import Session, time_to_filename, get_part_of_picture, get_session_names
# to resize images and save them
from scipy import ndimage, misc
# to time the process
import time
# to run subprocesses without dealing with spaces etc. by myself
import subprocess
# to save the amount of time things take
import json

def make_ocr_ready_images(sess, redo=False, part='digital reading'):
	reading_times = [x for x in sess.metadata if x['part'] == part]
	for reading_interval in reading_times:
		for image_time in reading_interval['transitions']:
			filename = time_to_filename(image_time)
			full_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + filename
			# check if we already made this image
			# (this script may be run multiple times if it didn't finish)
			# saving on image creation and running tesseract will help a lot with time
			dir_for_bigger_images = sess.dir_name + os.sep + settings.images_ready_for_ocr
			if not os.path.isdir(dir_for_bigger_images):
				os.mkdir(dir_for_bigger_images)
			full_path_for_new_image = dir_for_bigger_images + os.sep + filename
			resize_image(full_path, full_path_for_new_image, redo=redo, part=part)

def resize_dir(origin_dir, resized_dir, redo=False):
	for filename in os.listdir(origin_dir):
		resize_image(origin_dir + os.sep + filename, resized_dir + os.sep + filename, redo=redo)

def resize_image(original_path, resized_path, redo=False, part='digital reading'):
	if not redo and os.path.isfile(resized_path):
		return
	pic = get_part_of_picture(original_path, x_range=settings.x_range[part], y_range=settings.y_range[part])
	bigger_pic = ndimage.zoom(pic, (2, 2, 1), order=0)
	misc.imsave(resized_path, bigger_pic)

def run_tesseract(sess, redo=False, part='digital reading'):
	reading_times = [x for x in sess.metadata if x['part'] == part]
	for reading_interval in reading_times:
		for image_time in reading_interval['transitions']:
			filename = time_to_filename(image_time)
			image_dir = sess.dir_name + os.sep + settings.images_ready_for_ocr
			image_path = image_dir + os.sep + filename
			hocr_dir = sess.dir_name + os.sep + settings.hocr_dir
			if not os.path.isdir(hocr_dir):
				os.mkdir(hocr_dir)
			hocr_path = hocr_dir + os.sep + '.'.join(filename.split('.')[:-1])
			run_tesseract_on_image(image_path, hocr_path, redo)

def run_tesseract_on_image(image_path, hocr_path, redo=False):
	# check if we already made the hocr file
	# (this script may be run multiple times if it didn't finish)
	# saving on image creation and running tesseract will help a lot with time
	if not redo and os.path.isfile(hocr_path+'.hocr'):
		return
	command = ['tesseract', image_path, hocr_path, '-l', 'eng', 'hocr']
	subprocess.call(command)

def run_tesseract_on_dir(picture_dir, hocr_dir, redo=False):
	for filename in os.listdir(picture_dir):
		image_path = picture_dir + os.sep + filename
		hocr_path = hocr_dir + os.sep + '.'.join(filename.split('.')[:-1])
		run_tesseract_on_image(image_path, hocr_path)

# run all parts of run inital ocr and time them on each session
def run_initial_ocr_and_time(sess, part='digital reading'):
	time_to_build = {}
	t0 = time.time()
	make_ocr_ready_images(sess, redo=True, part=part)
	time_to_build['make_ocr_ready_images'] = time.time() - t0
	t0 = time.time()
	run_tesseract(sess, redo=True, part=part)
	time_to_build['run_tesseract'] = time.time() - t0
	time_to_build['find_digital_reading_transitions'] = time.time() - t0
	return time_to_build

def run_initial_ocr_and_time_on_each_session(redo=False):
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		if not redo and os.path.isfile(sess.dir_name + os.sep + 'time_to_run_initial_ocr.json'):
			continue
		time_to_build = run_initial_ocr_and_time(sess)
		with open(sess.dir_name + os.sep + 'time_to_run_initial_ocr.json', 'w') as fp:
			json.dump(time_to_build, fp)

if __name__ == '__main__':
	run_initial_ocr_and_time_on_each_session()

