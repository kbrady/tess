# to read about highlights
import json
from video_to_frames import Session, get_session_names
# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to save the output as a csv
import csv

def sess_name_to_id(sess):
	return sess.id.split('Scene_')[1].split('_Website')[0]

def get_final_highlights(sess):
	sess_id = sess_name_to_id(sess)

	with open(sess.dir_name + os.sep + 'highlighting_report.json', 'r') as infile:
		data = ' '.join([line for line in infile])
		data = json.loads(data)

	final_highlights = {}
	for time in data:
		for group in data[time]:
			words = zip(group['id_group'], group['text'].split(' '))
			if group['color'] == 'yellow':
				for w in words:
					final_highlights[w] = time
			elif group['color'] in ['white', 'dark blue']:
				for w in words:
					if w in final_highlights:
						del final_highlights[w]

	final_highlights = [(final_highlights[w], w) for w in final_highlights]
	final_highlights.sort()

	output = []
	current_list = []
	current_time = None

	for word_info in final_highlights:
		word = word_info[1]
		if current_time is None:
			current_time = word_info[0]
		if len(current_list) == 0 or (word_info[0] == current_time and word[0] == (current_list[-1][0] + 1)):
			current_list.append(word)
		else:
			highlight_string = ' '.join([w[1] for w in current_list])
			highlight_ids = ' '.join([str(w[0]) for w in current_list])
			output.append([highlight_string, highlight_ids, current_time])
			current_list = [word]
			current_time = word_info[0]

	highlight_string = ' '.join([w[1] for w in current_list])
	highlight_ids = ' '.join([str(w[0]) for w in current_list])
	output.append([highlight_string, highlight_ids, current_time])

	file_already_exists = os.path.isfile('final_highlights.csv')

	# save the output
	with open('final_highlights.csv', 'a') as outputfile:
		writer = csv.writer(outputfile, delimiter=',', quotechar='"')
		if not file_already_exists:
			writer.writerow(['user_id', 'highlight', 'word_ids', 'time'])
		for row in output:
			writer.writerow([sess_id] + row)

def get_final_highlights_for_each_session():
	# get the session names
	session_names = get_session_names()
	for sess_name in session_names:
		sess = Session(sess_name)
		# avoid sessions where the corrections have not been completely calculated
		if not os.path.isfile(sess.dir_name + os.sep + 'highlighting_report.json'):
			continue
		get_final_highlights(sess)


if __name__ == '__main__':
	get_final_highlights_for_each_session()
