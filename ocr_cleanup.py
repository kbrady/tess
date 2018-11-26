# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename, filename_to_time
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save reading times
import json
# to build documents
from Document import Document
# to build hash table for document discovery
from collections import defaultdict

# get lists of the lines in each correct file
def get_correct_bags(correct_corpus_directory = settings.correct_text_dir):
	correct_bags = {}
	for filename in os.listdir(correct_corpus_directory):
		filepath = correct_corpus_directory + os.sep + filename
		with open(filepath, 'r') as input_file:
			correct_bags[filename] = [l.strip() for l in input_file]
	return correct_bags

# this makes a mapping from words to the documents they appear in 
# it is used to quickly find the most likely document for files
def make_matching_dictionary(correct_bags):
	word_to_doc = defaultdict(set)
	for document_name in correct_bags:
		for line in correct_bags[document_name]:
			for word in line.split(' '):
				word_to_doc[word].add(document_name)
	return word_to_doc

# this function takes a set of documents and the
# correct documents they matched to and fixes then saves them
def cleanup_docs(doc_list, correct_bags, doc_index_to_filename_fun, right_shift=None, down_shift=None, scale=0.5, stop_at_lines=False, alt_dir_name=None):
	for doc_index in range(len(doc_list)):
		correct_filename = doc_index_to_filename_fun(doc_index)
		doc = doc_list[doc_index]
		doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
		# we want to have the option to just find matching lines and save to other filenames
		try:
			doc.fix(right_shift=right_shift, down_shift=down_shift, scale=scale, stop_at_lines=stop_at_lines)
		except Exception as e:
			doc.attrs['raised_error'] = 'Raised error while being fixed in cleanup_docs'
		doc.save(alt_dir_name=alt_dir_name)

# get the documents for a whole session
def get_documents(sess, redo=False, alt_dir_name=None, part='digital reading', source_dir_name=settings.hocr_dir, edit_dir=None):
	# need the session directory path to all the documents
	dir_name = sess.dir_name + os.sep + source_dir_name
	if edit_dir is not None:
		edit_dir_name = sess.dir_name + os.sep + edit_dir
	# if there are no hocr files to clean, we should move on
	if not os.path.isdir(dir_name):
		return []
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	# get the documents for this session
	documents = []
	bad_filepaths = []
	for time in reading_times:
		filename = time_to_filename(time, extension='hocr')
		if edit_dir is not None and os.path.isfile(edit_dir_name + os.sep + filename):
			filepath = edit_dir_name + os.sep + filename
		else:
			filepath = dir_name + os.sep + filename
		# don't re-calculate already finished files
		if not redo:
			alt_dir_name = alt_dir_name if alt_dir_name is not None else source_dir_name
			xml_path = sess.dir_name + os.sep + alt_dir_name + os.sep + filename
			if os.path.isfile(xml_path):
				continue
		# check to make sure the filepath is a valid document
		try:
			doc = Document(filepath, output_dir=alt_dir_name, output_dir_relative=True, time_in_seconds=filename_to_time(filepath))
			documents.append(doc)
		except Exception as e:
			bad_filepaths.append(filepath)
	# get rid of any documents which don't have lines
	# print(out how many of these there are)
	have_lines = [d for d in documents if (len(d.lines) > 0 and 'raised_error' not in d.attrs)]
	if len(bad_filepaths) > 0 or len(have_lines) < len(documents):
		print(len(bad_filepaths) + len(documents) - len(have_lines), 'bad documents in', dir_name)
		documents = have_lines
	return documents

# find the best matching correct document
def find_best_matching_correct_doc(documents, word_to_doc):
	# all the documents in a student session map to one correct document
	# find that document
	best_match = None
	for i in range(len(documents)):
		try:
			best_match = documents[i].find_correct(word_to_doc)
			break
		except Exception as e:
			continue
	if best_match is None:
		raise Exception('None of the words found by OCR match a document')
	# make a function that maps every document index to the best match
	return lambda x : best_match

# do the cleanup and save for a whole session
def cleanup_session(sess, correct_bags, word_to_doc, redo=False, scale=0.5, stop_at_lines=False, alt_dir_name=None, part='digital reading'):
	# time this action
	time_to_cleanup = {}
	t0 = time.time()
	# get the documents to correct
	alt_dir_name = alt_dir_name if alt_dir_name is not None else settings.xml_dir
	documents = get_documents(sess, redo=redo, alt_dir_name=alt_dir_name, part=part)
	time_to_cleanup['get_documents'] = time.time() - t0
	# if there are no documents to correct we are done
	if len(documents) == 0:
		return time_to_cleanup
	# get the correct document function
	t0 = time.time()
	doc_index_to_filename_fun = find_best_matching_correct_doc(documents, word_to_doc)
	time_to_cleanup['find_best_matching_correct_doc'] = time.time() - t0
	# cleanup all the documents
	t0 = time.time()
	right_shift = settings.x_range[part][0]
	down_shift = settings.y_range[part][0]
	cleanup_docs(documents, correct_bags, doc_index_to_filename_fun, right_shift=right_shift, down_shift=down_shift, scale=scale, stop_at_lines=stop_at_lines, alt_dir_name=alt_dir_name)
	time_to_cleanup['cleanup_docs'] = time.time() - t0
	return time_to_cleanup

def cleanup_hocr_files(input_dir_path, output_dir_path, correct_bags, word_to_doc, scale=0.5, stop_at_lines=False, alt_dir_name=None):
	# get the documents in this directory
	documents = []
	for filename in os.listdir(input_dir_path):
		filepath = input_dir_path + os.sep + filename
		if filename.endswith('.hocr'):
			documents.append(Document(filepath, output_dir=output_dir_path))
	# build the mapping function
	mapping = {}
	for i in range(len(documents)):
		mapping[i] = documents[i].find_correct(word_to_doc)
	doc_index_to_filename_fun = lambda x : mapping[x]
	# cleanup all the documents
	cleanup_docs(documents, correct_bags, doc_index_to_filename_fun, stop_at_lines=stop_at_lines, scale=scale, alt_dir_name=alt_dir_name)

def scale_docs(sess, dir_to_save=None, part='typing'):
	# need the session directory path to all the documents
	dir_name = sess.dir_name + os.sep + settings.hocr_dir
	# if there are no hocr files to clean, we should move on
	if not os.path.isdir(dir_name):
		return
	# get the documents in this directory
	documents = []
	for filename in os.listdir(dir_name):
		filepath = dir_name + os.sep + filename
		if filename.endswith('.hocr'):
			documents.append(Document(filepath, output_dir=dir_to_save))
	# scale to correct size
	right_shift = settings.x_range[part][0]
	down_shift = settings.y_range[part][0]
	right_shift = 0 if right_shift is None else right_shift
	down_shift = 0 if down_shift is None else down_shift
	# save documents
	for doc in documents:
		doc.scale(right_shift, down_shift, 0.5)
		doc.save()

def run_cleanup_session_and_time_on_each_session(redo=False, part='digital reading'):
	# get the correct bag names
	correct_bags = get_correct_bags()
	word_to_doc = make_matching_dictionary(correct_bags)
	# get the session names
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		if not redo and os.path.isfile(sess.dir_name + os.sep + 'time_to_cleanup_ocr.json'):
			continue
		time_to_cleanup = cleanup_session(sess, correct_bags, word_to_doc, redo=redo, stop_at_lines=False, alt_dir_name=None, part=part)
		with open(sess.dir_name + os.sep + 'time_to_cleanup_ocr.json', 'w') as fp:
			json.dump(time_to_cleanup, fp)

if __name__ == '__main__':
	run_cleanup_session_and_time_on_each_session(redo=True)
	# correct_bags = get_correct_bags()
	# word_to_doc = make_matching_dictionary(correct_bags)
	# cleanup_hocr_files('data/digital_reading_1/hocr-files', 'data/digital_reading_1/xml-files', correct_bags, word_to_doc, scale=1, stop_at_lines=False, alt_dir_name=None)
	# cleanup_hocr_files('data/digital_reading_2/hocr-files', 'data/digital_reading_2/xml-files', correct_bags, word_to_doc, scale=1, stop_at_lines=False, alt_dir_name=None)
	
