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
from Document import Document_XML

if __name__ == '__main__':
	sess_name = 'logging-with-div'

	sess = Session(sess_name)
	xml_dir = sess.dir_name + os.sep + settings.xml_dir
	output_dir = 'global_ids'
	old_doc = None
	filename_list = [f for f in os.listdir(xml_dir)]
	filename_list.sort()
	for filename in filename_list:
		xml_path = xml_dir + os.sep + filename
		doc = Document_XML(xml_path, None)
		if old_doc is None:
			for l in doc.lines:
				l.set_global_id(l.id)
			old_doc = doc
			continue
		# if there is a prev_doc
		doc.set_prev_lines(old_doc.lines)
		doc.assign_lines(correcting=False)
		doc.save(output_dir)
		old_doc = doc