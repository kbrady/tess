# to find files and run tesseract
import os
# to look in the right places
import settings
# to get the session info and find parts of an image
import video_to_frames
# to resize images and save them
from scipy import ndimage, misc

def make_ocr_ready_images(sess):
	digital_reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
	for reading_interval in digital_reading_times:
		for image_time in reading_interval['transitions']:
			filename = video_to_frames.time_to_filename(image_time)
			full_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + filename
			pic = video_to_frames.get_part_of_picture(full_path, x_range=[200, 1200], y_range=[40, 860])
			bigger_pic = ndimage.zoom(pic, (2, 2, 1), order=0)
			dir_for_bigger_images = sess.dir_name + os.sep + settings.images_ready_for_ocr
			if not os.path.isdir(dir_for_bigger_images):
				os.mkdir(dir_for_bigger_images)
			full_path_for_new_image = dir_for_bigger_images + os.sep + filename
			misc.imsave(full_path_for_new_image, bigger_pic)

if __name__ == '__main__':
	# some session ids from the pilot data
	pilot_sessions = ['seventh_participant', 'fifth_participant', 'third_student_participant', 'first_student_participant_second_take', 'first_student_participant', 'Amanda', 'eighth_participant', 'sixth_participant', 'fourth-participant-second-version' , 'fourth_participant', 'second_student_participant']

	for sess_name in pilot_sessions:
		sess = video_to_frames.Session(sess_name)
		make_ocr_ready_images(sess)