# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save output from some functions
import csv
# to build hash table for document discovery
from collections import defaultdict
# to read in xml files
from Document import Document

def assign_global_ids(sess, part='digital reading'):
	# need the session directory path to all the documents
	xml_dir_name = sess.dir_name + os.sep + settings.xml_dir
	alt_dir_name = settings.global_id_dir
	# get the times for this session
	reading_times = [x for x in sess.metadata if x['part'] == part]
	reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	reading_times.sort()
	# go through documents and assign global ids to words
	# for now two words are considered the same if they have the same text and the sequence is strictly increasing
	# I will continue thinking of more robust definitions
	# one word object can have multiple ids since it can contain multiple word snippets (if a space wasn't detected)
	word_context_to_id_map = defaultdict(list)
	largest_id = 0
	for t in reading_times:
		xml_path = xml_dir_name + os.sep + time_to_filename(t, extension='hocr')
		doc = Document(xml_path)
		word_series = [word for line in doc.lines for word in line.children if len(str(word)) > 0]
		for i in range(len(word_series)):
			word = word_series[i]
			word_strings = str(word).split(' ')
			global_ids = []
			for j in range(len(word_strings)):
				word_str = word_strings[j]
				if word_str not in word_context_to_id_map:
					word_context_to_id_map[word_str].append(largest_id)
					largest_id += 1
				possible_ids = word_context_to_id_map[word_str]
				if i == 0:# or 'global_ids' not in word_series[i-1].attrs:
					#if len(possible_ids) == 1:
					global_ids.append(min(possible_ids))
				else:
					ids_to_choose_from = [x for x in possible_ids if x > max(word_series[i-1].attrs['global_ids'])]
					if len(ids_to_choose_from) == 0:
						word_context_to_id_map[word_str].append(largest_id)
						ids_to_choose_from = [largest_id]
						largest_id += 1
					global_ids.append(min(ids_to_choose_from))
			word.attrs['global_ids'] = global_ids
		# go through a second time backwards to check that assigned ids are as good as possible
		for i in range(len(word_series)-1,-1,-1):
			word = word_series[i]
			global_ids = word.attrs['global_ids']
			word_strings = str(word).split(' ')
			for j in range(len(word_strings)-1,-1,-1):
				word_str = word_strings[j]
				assigned_id = word.attrs['global_ids'][j]
				possible_ids = word_context_to_id_map[word_str]
				if len(possible_ids) > 1:
					if i == len(word_series)-1:
						continue
					try:
						best_id = max([x for x in possible_ids if x < min(word_series[i+1].attrs['global_ids'])])
					except Exception as e:
						print(possible_ids)
						print(word_series[i+1].attrs['global_ids'])
						print(assigned_id)
						print(word)
						print(word_series[i+1])
						print(xml_path)
						raise e
					global_ids[j] = best_id
			word.attrs['global_ids'] = global_ids
		doc.save(alt_dir_name=alt_dir_name)

if __name__ == '__main__':
	for sess_name in os.listdir('data'):
		if sess_name.startswith('.'):
			continue
		print(sess_name)
		sess = Session(sess_name)
		assign_global_ids(sess)
	# check the outcome
	# alt_dir_name = sess.dir_name + os.sep + settings.global_id_dir
	# # get the times for this session
	# reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
	# reading_times = [t for reading_interval in reading_times for t in reading_interval['transitions']]
	# reading_times.sort()
	# t = reading_times[-20]
	# xml_path = alt_dir_name + os.sep + time_to_filename(t, extension='hocr')
	# doc = Document(xml_path)
	# # get the word series
	# word_series = [word for line in doc.lines for word in line.children if len(str(word).strip()) > 0]
	# for word in word_series:
	# 	try:
	# 		print(word.attrs['global_ids'], str(word))
	# 	except KeyError as e:
	# 		print(word)
	# 		print(word.attrs)
	# 		print(word.title)
	# 		raise e