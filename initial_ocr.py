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

def make_ocr_ready_images(sess, redo=False):
	digital_reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
	for reading_interval in digital_reading_times:
		for image_time in reading_interval['transitions']:
			filename = video_to_frames.time_to_filename(image_time)
			full_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + filename
			# check if we already made this image
			# (this script may be run multiple times if it didn't finish)
			# saving on image creation and running tesseract will help a lot with time
			dir_for_bigger_images = sess.dir_name + os.sep + settings.images_ready_for_ocr
			full_path_for_new_image = dir_for_bigger_images + os.sep + filename
			if not redo and os.path.isfile(full_path_for_new_image):
				continue
			pic = video_to_frames.get_part_of_picture(full_path, x_range=settings.digital_reading_x_range, y_range=settings.digital_reading_y_range)
			bigger_pic = ndimage.zoom(pic, (2, 2, 1), order=0)
			if not os.path.isdir(dir_for_bigger_images):
				os.mkdir(dir_for_bigger_images)
			misc.imsave(full_path_for_new_image, bigger_pic)

def run_tesseract(sess, redo=False):
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
			run_tesseract_on_image(image_path, hocr_path, redo)

def run_tesseract_on_image(image_path, hocr_path, redo=False):
	# check if we already made the hocr file
	# (this script may be run multiple times if it didn't finish)
	# saving on image creation and running tesseract will help a lot with time
	if not redo and os.path.isfile(hocr_path+'.hocr'):
		return
	command = ['tesseract', image_path, hocr_path, '-l', 'eng', 'hocr']
	subprocess.call(command)

if __name__ == '__main__':
	# some session ids from the pilot data
	all_sessions = video_to_frames.get_session_names()

	t0 = time.time()
	for sess_name in all_sessions:
		print sess_name
		sess = video_to_frames.Session(sess_name)
		make_ocr_ready_images(sess)
		run_tesseract(sess)
	t1 = time.time()
	print 'time taken', t1 - t0

