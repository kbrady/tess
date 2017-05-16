# to find files and parse paths correctly
import os
# to look in the right places
import settings
# to get the session info
from video_to_frames import Session
# to read hocr files and write xml files
from bs4 import BeautifulSoup
# to write corrected output to file
import xml.etree.cElementTree as ET
# to make word frequency vectors
from collections import Counter
# to convert characters to ascii
import unicodedata
# to measure how long each session is taking
import time

# to handle unicode characters that unicodedata doesn't catch
Replacement_Dict = {u'\u2014':'-'}

def replace_unicode(text):
	for k in Replacement_Dict:
		text = text.replace(k, Replacement_Dict[k])
	return text

# a class to store, interpret and scale bounding boxes
class BBox:
	def __init__(self, info):
		if type(info) == str or type(info) == unicode:
			info = [int(x) for x in info.split(' ')]
		try:
			self.right, self.top, self.left, self.bottom = info
		except Exception as e:
			print type(info)
			print info
			raise e
		self.str_rep = ' '.join([str(x) for x in info])

	def __str__(self):
		return self.str_rep

# A parent object for lines and words which defines some shared functionality
class Part(object):
	def __init__(self, tag):
		info = tag['title'].split('; ')
		self.bbox = BBox(info[0][info[0].find(' ')+1:])
		self.id = tag['id']

	def levenshteinDistance(self, s2):
		s1 = str(self)
		if len(s1) == 0:
			return 1.0
		if len(s1) > len(s2):
			s1, s2 = s2, s1

		distances = range(len(s1) + 1)
		for i2, c2 in enumerate(s2):
			distances_ = [i2+1]
			for i1, c1 in enumerate(s1):
				if c1 == c2:
					distances_.append(distances[i1])
				else:
					distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
			distances = distances_
		return float(distances[-1])/max([len(s1), len(s2)])

	def find_matching(self, all_strings):
		all_strings = [(self.levenshteinDistance(all_strings[i]), all_strings[i], i) for i in range(len(all_strings))]
		return min(all_strings)

# An object to interpret words in hocr files
class Word(Part):
	def __init__(self, tag, et_parent=None):
		super(self.__class__, self).__init__(tag)
		# set text and clean up by changing all text to ascii (assuming we are working in English for the moment)
		self.text = tag.get_text()
		self.text = replace_unicode(self.text)
		self.text = unicodedata.normalize('NFKD', self.text).encode('ascii','ignore')
		self.corrected_text = None
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, "word", bbox=str(self.bbox))
		else:
			self.et = ET.Element("word", bbox=str(self.bbox))
		self.et.text = self.text

	def __repr__(self):
		if self.corrected_text is not None:
			return self.corrected_text
		return ''.join(filter(lambda x:ord(x) < 128, self.text))

	def assign_matching(self, text):
		self.corrected_text = text
		self.et.text = text

# An object to interpret lines in hocr files
class Line(Part):
	def __init__(self, tag, et_parent=None):
		super(self.__class__, self).__init__(tag)
		self.updated_line = '' 
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, "line", bbox=str(self.bbox))
		else:
			self.et = ET.Element("line", bbox=str(self.bbox))
		self.children = [Word(sub_tag, self.et) for sub_tag in tag.find_all('span', {'class':'ocrx_word'})]
		self.word_hist = Counter([str(c) for c in self.children])
		self.letter_hist = Counter(str(self))
	
	def __repr__(self):
		return ' '.join([str(word) for word in self.children])

	def assign_matching(self, string):
		self.updated_line = string
		assign(self.children, string.split(' '), complete_coverage=True)

# An object to interpret hocr files
class Document:
	def __init__(self, tesseract_file):
		# save the location of the original file
		self.tesseract_file = tesseract_file
		if not tesseract_file.endswith('.hocr'):
			raise Exception(tesseract_file+' is not of type .hocr')
		# save the locaiton where corrected files will be saved to
		xml_dir = os.sep.join(tesseract_file.split(os.sep)[:-2]) + os.sep + settings.xml_dir
		if not os.path.isdir(xml_dir):
			os.mkdir(xml_dir)
		self.xml_file = xml_dir + os.sep + tesseract_file.split(os.sep)[-1][:-len('.hocr')] + '.xml'
		# make a root to build the xml for the corrected file
		self.root = ET.Element("root")
		# open the hocr file and read in the output from tesseract
		with open(tesseract_file, 'r') as input_file:
			data = ' '.join([line for line in input_file])
			soup = BeautifulSoup(data, "html.parser")
			tag_list = soup.find_all('span', {'class':'ocr_line'})
			self.lines = [Line(t, self.root) for t in tag_list]
		self.correct_lines = []

	def __str__(self):
		return '\n'.join([str(l) for l in self.lines])

	def find_correct(self, correct_bags=None):
		bag_of_lines = [str(l) for l in self.lines]
		for correct_filename in correct_bags:
			num_same = len(set(correct_bags[correct_filename]) & set(bag_of_lines))
			perc_same = float(num_same)/len(bag_of_lines)
			# may need to work on cuttoff
			if perc_same > .5:
				self.assign_correct_bag(correct_filename, correct_bags[correct_filename])
				return correct_filename, correct_bags[correct_filename]
		raise Exception('Could not find file match for '+self.tesseract_file)

	def assign_correct_bag(self, correct_filename, correct_lines):
		self.root.set('filename', correct_filename)
		self.correct_lines = correct_lines

	def save(self):
		tree = ET.ElementTree(self.root)
		tree.write(self.xml_file)

# get lists of the lines in each correct file
def get_correct_bags():
	correct_bags = {}
	for filename in os.listdir('correct_text'):
		filepath = 'correct_text' + os.sep + filename
		with open(filepath, 'r') as input_file:
			correct_bags[filename] = [l.strip() for l in input_file]
	return correct_bags

# A function to clean up all the hocr files for a session
def cleanup(sess):
	correct_bags = get_correct_bags()
	dir_name = sess.dir_name + os.sep + settings.hocr_dir
	correct_filename = None
	correct_lines = None
	for filename in os.listdir(dir_name):
		filepath = dir_name + os.sep + filename
		document = Document(filepath)
		if correct_filename is None:
			correct_filename, correct_lines = document.find_correct(correct_bags)
		else:
			document.assign_correct_bag(correct_filename, correct_lines)
		document.save()

if __name__ == '__main__':
	# some session ids from the pilot data
	pilot_sessions = ['seventh_participant', 'fifth_participant', 'third_student_participant', 'first_student_participant_second_take', 'first_student_participant', 'Amanda', 'eighth_participant', 'sixth_participant', 'fourth-participant-second-version' , 'fourth_participant', 'second_student_participant']

	t0 = time.time()
	for sess_name in pilot_sessions:
		sess = Session(sess_name)
		cleanup(sess)
		break
	t1 = time.time()
	print 'time taken', t1 - t0
