# to read in xml files
from Document import Document_XML
# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session, get_session_names, time_to_filename
# to dump a dictionary
import json

def get_changes(my_lines, old_lines):
	filter = lambda l: [x.strip() for x in l if len(x.strip()) > 0]
	new_lines = filter([my_lines[k] for k in my_lines if k not in old_lines])
	deleted_lines = filter([old_lines[k] for k in old_lines if k not in my_lines])
	editted_lines = filter([my_lines[k] for k in my_lines if (k in old_lines) and (my_lines[k] != old_lines[k])])
	return new_lines, deleted_lines, editted_lines

if __name__ == '__main__':
	sess_name = 'logging-with-div'

	output = {}
	sess = Session(sess_name)
	xml_dir = sess.dir_name + os.sep + 'global_ids'
	old_doc = None
	filename_list = [f for f in os.listdir(xml_dir)]
	filename_list.sort()
	for filename in filename_list:
		xml_path = xml_dir + os.sep + filename
		doc = Document_XML(xml_path, None)
		if old_doc is None:
			old_doc = doc
			continue
		# if there is a prev_doc
		my_lines = dict([(l.attrs['global_id'], str(l)) for l in doc.lines if float(l.attrs['top']) > 119])
		old_lines = dict([(l.attrs['global_id'], str(l)) for l in old_doc.lines if float(l.attrs['top']) > 119])
		time = filename[:-4]
		new_lines, deleted_lines, editted_lines = get_changes(my_lines, old_lines)
		if (len(new_lines) + len(deleted_lines) + len(editted_lines)) > 0:
			output[time] = new_lines, deleted_lines, editted_lines
		old_doc = doc
		
	with open('edits.json', 'w') as outfile:
		json.dump(output, outfile)