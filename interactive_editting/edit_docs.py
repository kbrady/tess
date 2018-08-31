import os
import sys
sys.path.append('..')
from Document import Document
from local_paths import highlight_color_pairs
from video_to_frames import time_to_filename, Session, filename_to_time
import json
from matplotlib import image as mpimg
from flask import Flask, render_template, url_for, request, redirect
import settings
import time
from random import randint
from collections import Counter

app = Flask(__name__)

def word_to_json(word, index):
	output = {}
	right, left, top, bottom = word.title['bbox'].right, word.title['bbox'].left, word.title['bbox'].top, word.title['bbox'].bottom
	output['right'], output['left'], output['top'], output['bottom'] = int(right), int(left), int(top), int(bottom)
	output['text'] = word.text
	output['highlight'] = word.attrs['highlight'] if 'highlight' in word.attrs else 'white'
	output['global_ids'] = str(index)
	return output

def is_out_of_bounds(word_dict, img_shape):
	height, width, _ = img_shape
	# make sure we aren't violating physics
	for val in ['right', 'left']:
		if word_dict[val] >= width:
			return True
	for val in ['top', 'bottom']:
		if word_dict[val] >= height:
			return True
	return False

def word_list_as_json(doc, img_shape):
	all_words = [w for l in doc.lines for w in l.children]
	word_dict = [word_to_json(all_words[i], i) for i in range(len(all_words))]
	word_dict = [x for x in word_dict if not is_out_of_bounds(x, img_shape)]
	return word_dict

def rgb2hex(rgb):
	return '#%02x%02x%02x' % rgb

def get_num_highlights(filetime):
	filepath = sess.dir_name + os.sep + source_dirs[0] + os.sep + time_to_filename(filetime, extension='hocr')
	doc = Document(filepath, calc_width=False)
	highlights = Counter([w.attrs['highlight'] for l in doc.lines for w in l.children])
	return highlights

def compare_counts(h_counts1, h_counts2):
	output = 0
	for k in highlight_color_pairs:
		if k == 'white':
			continue
		output += abs(h_counts1[k] - h_counts2[k])
	return output

# global variables
sess = None
editor_folder = ''
reading_times = None
reading_index = 0
edit_start_time = None
source_dirs = ['highlight-no-ids', 'highlight-no-correction']
source_dir_index = 0

@app.route('/')
def home():
	sess_names = []
	for folder_name in os.listdir(settings.data_dir):
		if folder_name.startswith('.'):
			continue
		if os.path.isdir(settings.data_dir + os.sep + folder_name):
			sess_names.append(folder_name)

	return render_template('home.html', sess_names=sess_names)

@app.route('/set_session', methods=['POST'])
def set_session():
	global editor_folder, sess, reading_times, reading_index
	if request.method == 'POST':
		editor = request.form['editor'] + '_edits'
		sess_name = request.form['session']
		sess = Session(sess_name)
		continue_from_last = request.form['continue_from_last']

		# make the folder to save the editted files in
		editor_folder = sess.dir_name + os.sep + editor
		if not os.path.isdir(editor_folder):
			os.mkdir(editor_folder)

		# get the reading times
		reading_times = [t for x in sess.metadata for t in x.get('transitions', []) if x['part'] == 'digital reading']
		# sort according to number of changed highlights
		highlight_counts = [get_num_highlights(t) for t in reading_times]
		highlight_keys = [0] + [compare_counts(highlight_counts[i], highlight_counts[i-1]) for i in range(1, len(highlight_counts))]
		keys_and_times = list(zip(highlight_keys, reading_times))
		keys_and_times.sort(reverse = True)
		reading_times = [pair[1] for pair in keys_and_times]
		# set the index
		reading_index = 0

		# skip files that have already been reviewed
		if continue_from_last:
			already_done = [filename_to_time(x) for x in os.listdir(editor_folder) if not x.startswith('.')]
			while reading_times[reading_index] in already_done:
				reading_index += 1
				# we have already gone through all the files, go home
				if reading_index >= len(reading_times):
					print('done')
					return redirect('/')
		return redirect('/doc')
	# if no data was sent, go home
	return redirect('/')

@app.route('/doc')
def edit_doc():
	global edit_start_time, source_dir_index
	edit_start_time = time.time()
	filetime = reading_times[reading_index]
	# display the already editted document if it exists
	to_save_to = sess.dir_name + os.sep + editor_folder + os.sep + time_to_filename(filetime, extension='hocr')
	if os.path.isfile(to_save_to):
		filepath = to_save_to
	else:
		source_dir_index = randint(0, len(source_dirs)-1)
		filepath = sess.dir_name + os.sep + source_dirs[source_dir_index] + os.sep + time_to_filename(filetime, extension='hocr')
	doc = Document(filepath)
	img_path = sess.dir_name + os.sep + settings.frame_images_dir + os.sep + time_to_filename(filetime, extension='jpg')
	img = mpimg.imread(img_path)
	img_save_path = 'static/imgs/' + sess.id + '_' + time_to_filename(filetime, extension='jpg')
	mpimg.imsave(img_save_path, img)

	# get the color hex numbers
	color_mapping = [[k, rgb2hex(highlight_color_pairs[k][0]), rgb2hex(highlight_color_pairs[k][1])] for k in highlight_color_pairs]

	# data
	data = {'wordInfo': word_list_as_json(doc, img.shape), 'imgSize': list(img.shape), 'colors': color_mapping, 'imgPath':img_save_path}

	return render_template('view_doc.html', data=data)

@app.route('/save_doc', methods=['POST'])
def save_doc():
	global reading_index
	if request.method == 'POST':
		# get time spent editting in seconds
		time_spent_editting = time.time() - edit_start_time

		if len(request.form['changes_dict']) == 0:
			changes = {}
		else:
			changes = eval(request.form['changes_dict'])
		button = request.form['button']

		# open document
		filetime = reading_times[reading_index]
		# open the already editted document if it exists
		to_save_to = sess.dir_name + os.sep + editor_folder + os.sep + time_to_filename(filetime, extension='hocr')
		if os.path.isfile(to_save_to):
			filepath = to_save_to
		else:
			filepath = sess.dir_name + os.sep + source_dirs[source_dir_index] + os.sep + time_to_filename(filetime, extension='hocr')
		doc = Document(filepath, output_dir=editor_folder)
		if 'seconds_spent_editting' in doc.attrs:
			time_spent_editting += eval(doc.attrs['seconds_spent_editting'])
		doc.attrs['seconds_spent_editting'] = time_spent_editting
		# record the path of the file that was editted
		if not os.path.isfile(to_save_to):
			doc.attrs['editted_from_path'] = filepath
		all_words = [w for l in doc.lines for w in l.children]

		# make changes
		for id_key in changes:
			index = int(id_key)
			all_words[index].text = changes[id_key][0]
			all_words[index].attrs['highlight'] = changes[id_key][1]
			all_words[index].attrs['editted_by_human'] = 'True'
		# save changes
		doc.save()

		#iterate index
		if button == 'Next':
			if reading_index + 1 < len(reading_times):
				reading_index += 1
				return redirect('/doc')
			else:
				return redirect('/')
		else:
			if reading_index > 0:
				reading_index -= 1
				return redirect('/doc')
			else:
				return redirect('/')
	# if no data was sent, go home
	return redirect('/')

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')