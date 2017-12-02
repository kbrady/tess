# to get the session info
from video_to_frames import Session, get_session_names
# to record
import csv

if __name__ == '__main__':
	all_sesion_names = get_session_names()

	all_times = []
	for sess_name in all_sesion_names:
		sess = Session(sess_name)
		reading_times = [x for x in sess.metadata if x['part'] == 'digital reading']
		if len(reading_times) == 0:
			start_time = None
			end_time = None
		else:
			start_time = min([x['start_time'] for x in reading_times])
			end_time = max([x['end_time'] for x in reading_times])
		all_times.append([sess_name, start_time, end_time])
	with open('reading_times.csv', 'w') as outfile:
		writer = csv.writer(outfile)
		writer.writerow(['sess_name', 'start_time', 'end_time'])
		for row in all_times:
			writer.writerow(row)
