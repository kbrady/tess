# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save output from some functions
import csv
# to build documents
from Document import Document
# to build hash table for document discovery
from collections import defaultdict

# get lists of the lines in each correct file
def get_correct_bags():
	correct_bags = {}
	for filename in os.listdir('correct_text'):
		filepath = 'correct_text' + os.sep + filename
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
def cleanup_docs(doc_list, correct_bags, doc_index_to_filename_fun):
	for doc_index in range(len(doc_list)):
		correct_filename = doc_index_to_filename_fun(doc_index)
		doc = doc_list[doc_index]
		doc.assign_correct_bag(correct_filename, correct_bags[correct_filename])
		doc.fix()
		doc.save()

# do the cleanup and save for a whole session
def cleanup_session(sess, correct_bags, word_to_doc):
	# need the session directory path to all the documents
	dir_name = sess.dir_name + os.sep + settings.hocr_dir
	# get the documents for this session
	documents = []
	for filename in os.listdir(dir_name):
		filepath = dir_name + os.sep + filename
		documents.append(Document(filepath))
	# all the documents in a student session map to one correct document
	# find that document
	best_match = documents[0].find_correct(word_to_doc)
	# make a function that maps every document index to the best match
	doc_index_to_filename_fun = lambda x : best_match
	# cleanup all the documents
	cleanup_docs(documents, correct_bags, doc_index_to_filename_fun)

def cleanup_hocr_files(input_dir_path, output_dir_path, correct_bags, word_to_doc):
	# get the documents in this directory
	documents = []
	for filename in os.listdir(input_dir_path):
		filepath = input_dir_path + os.sep + filename
		if filename.endswith('.hocr'):
			documents.append(Document(filepath, xml_dir=output_dir_path))
	# build the mapping function
	mapping = {}
	for i in range(len(documents)):
		mapping[i] = documents[i].find_correct(word_to_doc)
	doc_index_to_filename_fun = lambda x : mapping[x]
	# cleanup all the documents
	cleanup_docs(documents, correct_bags, doc_index_to_filename_fun)

if __name__ == '__main__':
	correct_bags = get_correct_bags()
	word_to_doc = make_matching_dictionary(correct_bags)
	cleanup_hocr_files('test-data', 'test-output', correct_bags, word_to_doc)
	
