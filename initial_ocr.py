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
# to save the amount of time things take
import csv

def make_ocr_ready_images(sess, redo=False, part='digital reading'):
	reading_times = [x for x in sess.metadata if x['part'] == part]
	for reading_interval in reading_times:
		for image_time in reading_interval['transitions']:
			filename = video_to_frames.time_to_filename(image_time)
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
	pic = video_to_frames.get_part_of_picture(original_path, x_range=settings.x_range[part], y_range=settings.y_range[part])
	bigger_pic = ndimage.zoom(pic, (2, 2, 1), order=0)
	misc.imsave(resized_path, bigger_pic)

def run_tesseract(sess, redo=False, part='digital reading'):
	reading_times = [x for x in sess.metadata if x['part'] == part]
	for reading_interval in reading_times:
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

def run_tesseract_on_dir(picture_dir, hocr_dir, redo=False):
	for filename in os.listdir(picture_dir):
		image_path = picture_dir + os.sep + filename
		hocr_path = hocr_dir + os.sep + '.'.join(filename.split('.')[:-1])
		run_tesseract_on_image(image_path, hocr_path)

if __name__ == '__main__':
	# some session ids from the pilot data
	sess_name = 'logging-with-div'

	sess = video_to_frames.Session(sess_name)
	make_ocr_ready_images(sess, redo=False, part='typing')
	run_tesseract(sess, redo=False, part='typing')

	# with open('tesseract_times.csv', 'w') as outputfile:
	# 	writer = csv.writer(outputfile, delimiter=',', quotechar='"')
	# 	writer.writerow(['sess_name', 'time'])
	# 	for sess_name in all_sessions:
	# 		t0 = time.time()
	# 		sess = video_to_frames.Session(sess_name)
	# 		run_tesseract(sess, redo=True)
	# 		t1 = time.time()
	# 		writer.writerow([sess_name, t1 - t0])

