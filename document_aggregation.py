# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename
# to get the correct document paths
from ocr_cleanup import get_correct_bags, get_documents
# to measure how long each session is taking
import time
# to calculate the standard deviation of dimensions
import numpy as np
# to save output from some functions
import json
# to build hash table for document discovery
from collections import defaultdict
# to read in xml files
from Document import Document

def get_word_to_id_assignment(correct_doc_path):
	mapping = defaultdict(list)
	with open(correct_doc_path, 'r') as infile:
		index = 0
		for line in infile:
			for word in line.split(' '):
				mapping[word.strip()].append(index)
				index += 1
	return mapping

def get_assigned_global_ids(word_series, lower_index=0, upper_index=None):
	output = []
	upper_index = len(word_series) if upper_index is None else upper_index
	for word in word_series[lower_index:upper_index]:
		if 'global_ids' not in word.attrs:
			continue
		global_ids = word.attrs['global_ids']
		if type(global_ids) is not list:
			global_ids = global_ids.split(' ')
		global_ids = [int(x) for x in global_ids]
		output += global_ids
	return output

# find the answer with backtracking when it cannot be found using straight forward methods
def get_words_and_assignments(word_series):
	output = []
	for word in word_series:
		if 'global_ids' not in word.attrs:
			output.append((str(word), []))
			continue
		global_ids = word.attrs['global_ids']
		if type(global_ids) is not list:
			global_ids = global_ids.split(' ')
		global_ids = [int(x) for x in global_ids]
		output.append((str(word), global_ids))
	return output

def find_assignment_with_backtracking(words_and_assignments, mapping, max_possible_value):
	# loop through the words until all are matched
	unassigned_indexes = [i for i in range(len(words_and_assignments)) if len(words_and_assignments[i][1]) == 0]
	while len(unassigned_indexes) > 0:
		# assign any words that only map to one word
		for i in unassigned_indexes:
			# find the bracketing indexes
			assigned_lower_ids = [g_id for pair in words_and_assignments[:i] for g_id in pair[1]]
			assigned_upper_ids = [g_id for pair in words_and_assignments[i:] for g_id in pair[1]]
			lower_bound = max(assigned_lower_ids) if len(assigned_lower_ids) > 0 else -1
			upper_bound = min(assigned_upper_ids) if len(assigned_upper_ids) > 0 else max_possible_value+1
			# break the word text into snippets
			snippets = words_and_assignments[i][0].split(' ')
			for snippet_index in range(len(snippets)):
				possible_values = [g_id for g_id in mapping[snippets[snippet_index]] if lower_bound < g_id and upper_bound > g_id]
				# if this assignment leads to a conflict, return None
				if len(possible_values) == 0:
					return None
				if len(possible_values) == 1:
					global_val = possible_values[0]
					global_indexes = [global_val - snippet_index + x for x in range(len(snippets))]
					words_and_assignments[i] = (words_and_assignments[i][0], global_indexes)
					break
		new_unassigned_indexes = [i for i in range(len(words_and_assignments)) if len(words_and_assignments[i][1]) == 0]
		if len(new_unassigned_indexes) == len(unassigned_indexes):
			# make an assignment and continue exploring
			index_to_assign = new_unassigned_indexes[0]
			# find the bracketing indexes
			assigned_lower_ids = [g_id for pair in words_and_assignments[:index_to_assign] for g_id in pair[1]]
			assigned_upper_ids = [g_id for pair in words_and_assignments[index_to_assign:] for g_id in pair[1]]
			lower_bound = max(assigned_lower_ids) if len(assigned_lower_ids) > 0 else -1
			upper_bound = min(assigned_upper_ids) if len(assigned_upper_ids) > 0 else max_possible_value+1
			# get the snippets
			snippets = words_and_assignments[index_to_assign][0].split(' ')
			# only look at assignments for the first snippet
			possible_values = [g_id for g_id in mapping[snippets[0]] if lower_bound < g_id and upper_bound > g_id]
			for global_val in possible_values:
				new_words_and_assignments = words_and_assignments.copy()
				global_indexes = [global_val + x for x in range(len(snippets))]
				new_words_and_assignments[index_to_assign] = (words_and_assignments[index_to_assign][0], global_indexes)
				result = find_assignment_with_backtracking(new_words_and_assignments, mapping, max_possible_value)
				if result is not None:
					return result
			# if no solution exists, return None
			return None
		unassigned_indexes = new_unassigned_indexes
	return words_and_assignments

def assign_global_ids_to_doc(doc, mapping, max_possible_value, error_dir):
	word_series = [word for line in doc.lines for word in line.children if len(str(word)) > 0]
	# loop through the words until all are matched
	unassigned_words = [w for w in word_series if 'global_ids' not in w.attrs]
	while len(unassigned_words) > 0:
		# assign any words that only map to one word
		for i in range(len(word_series)):
			if 'global_ids' in word_series[i].attrs:
				continue
			# find the bracketing indexes
			assigned_lower_ids = get_assigned_global_ids(word_series, upper_index=i)
			assigned_upper_ids = get_assigned_global_ids(word_series, lower_index=i)
			lower_bound = max(assigned_lower_ids) if len(assigned_lower_ids) > 0 else -1
			upper_bound = min(assigned_upper_ids) if len(assigned_upper_ids) > 0 else max_possible_value+1
			# break the word text into snippets
			snippets = str(word_series[i]).split(' ')
			for snippet_index in range(len(snippets)):
				possible_values = [g_id for g_id in mapping[snippets[snippet_index]] if lower_bound < g_id and upper_bound > g_id]
				if len(possible_values) == 0:
					word_series[i].attrs['global_ids'] = [-1]
					word_series[i].attrs['error'] = 'probably'
					doc.save(alt_dir_name=error_dir)
					print('No ids found for {} in {}'.format(snippets[snippet_index], str(doc.find_title_attribute('image'))))
				if len(possible_values) == 1:
					global_val = possible_values[0]
					global_indexes = [global_val - snippet_index + x for x in range(len(snippets))]
					word_series[i].attrs['global_ids'] = global_indexes
					break
		new_unassigned_words = [w for w in word_series if 'global_ids' not in w.attrs]
		if len(new_unassigned_words) == len(unassigned_words):
			# look for solution with backtracking
			backtracking_result = find_assignment_with_backtracking(get_words_and_assignments(word_series), mapping, max_possible_value)
			if backtracking_result is not None:
				for i in range(len(word_series)):
					word_series[i].attrs['global_ids'] = backtracking_result[i][1]
				print('Used backtracking to solve {}'.format(str(doc.find_title_attribute('image'))))
				return
			doc.save(alt_dir_name=error_dir)
			print('Entered infinite loop for {}'.format(str(doc.find_title_attribute('image'))))
		unassigned_words = new_unassigned_words

# use the correct file to assign global ids
def assign_global_ids_from_correct_file(sess, part='digital reading', redo=False, error_dir=settings.error_dir):
	documents = get_documents(sess, source_dir_name=settings.xml_dir, alt_dir_name = settings.global_id_dir)
	if len(documents) == 0:
		return
	mapping = get_word_to_id_assignment(settings.correct_text_dir + os.sep + documents[0].attrs['filename'])
	max_possible_value = max([g_id for id_list in mapping.values() for g_id in id_list])
	for doc in documents:
		if not redo:
			if os.path.isfile(doc.output_file):
				continue
		assign_global_ids_to_doc(doc, mapping, max_possible_value, error_dir)

def assign_global_ids_to_each_session(redo=False, part='digital reading', error_dir=settings.error_dir):
	# get the session names
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		if not redo and os.path.isfile(sess.dir_name + os.sep + 'time_to_assign_ids.json'):
			continue
		time_to_assign_ids = {}
		t0 = time.time()
		assign_global_ids_from_correct_file(sess, part=part, redo=redo, error_dir=error_dir)
		time_to_assign_ids['assign_global_ids_from_correct_file'] = time.time() - t0
		with open(sess.dir_name + os.sep + 'time_to_assign_ids.json', 'w') as fp:
			json.dump(time_to_assign_ids, fp)

def assign_global_ids(sess, part='digital reading', redo=False):
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
		# don't recalculate already saved files
		if not redo:
			path_to_save_to = alt_dir_name + os.sep + time_to_filename(t, extension='hocr')
			if os.path.exists(path_to_save_to):
				continue
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
	assign_global_ids_to_each_session()