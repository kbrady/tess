# to write corrected output to file
import xml.etree.cElementTree as ET
# to read hocr files and write xml files
from bs4 import BeautifulSoup
# to build title attributes
from TitleAttr import TitleAttr
# for bounding box functionality
from BBox import BBox
# to convert characters to ascii
import unicodedata

# to handle unicode characters that unicodedata doesn't catch
Replacement_Dict = {u'\u2014':'-'}

def replace_unicode(text):
	if text is None:
		return ''
	for k in Replacement_Dict:
		text = text.replace(k, Replacement_Dict[k])
	return text

# A master template for saving all XML type tags
class XML_META(object):
	def __init__(self, tag, parent=None, class_rules=None):
		# read the tag and all it's attributes
		self.tag_name = tag.name
		self.text = tag.string
		# for the moment I am removing unicode from the text (will need to fix)
		self.clean_text()
		self.attrs = {}
		# title attributes are spetial
		self.title = {}
		for k in tag.attrs:
			if k == 'title':
				for title_attr in tag.attrs[k].split('; '):
					split_place = title_attr.find(' ')
					name = title_attr[:split_place]
					values = title_attr[split_place+1:]
					self.title[name] = TitleAttr(name, values) if name != 'bbox' else BBox(name, values)
			else:
				self.attrs[k] = tag.attrs[k]
		self.id = self.attrs.get('id', None)
		# keep track of parents
		self.parent = parent
		self.children = []
		class_rules = {} if class_rules is None else class_rules
		for c in tag.children:
			if str(type(c)) != "<class 'bs4.element.Tag'>":
				continue
			class_to_use = XML_META
			for class_val in c.get('class', [None]):
				if class_val in class_rules:
					class_to_use = class_rules[class_val]
					break
			self.children.append(class_to_use(c, parent=self, class_rules=class_rules))

	# some attributes are stored in children of the document, this function finds them
	def find_attribute(self, attr_name):
		if attr_name in self.attrs:
			return self.attrs[attr_name]
		for c in self.children:
			val = c.find_attribute(attr_name)
			if val is not None:
				return val
		return None

	# some title attributes are stored in children of the document, this function finds them
	def find_title_attribute(self, attr_name):
		if attr_name in self.title:
			return self.title[attr_name].values
		for c in self.children:
			val = c.find_title_attribute(attr_name)
			if val is not None:
				return val
		return None

	# set text and clean up by changing all text to ascii (assuming we are working in English for the moment)
	def clean_text(self):
		self.text = replace_unicode(self.text)
		# if type(self.text) == unicode:
		# 	self.text = unicodedata.normalize('NFKD', self.text).encode('ascii','ignore')

	# some functions to interface with the bounding box
	def width(self):
		return self.title['bbox'].right - self.title['bbox'].left

	def height(self):
		return self.title['bbox'].bottom - self.title['bbox'].top

	def scale(self, right_shift, down_shift, multiple, scale_children=True):
		if 'bbox' in self.title:
			self.title['bbox'].scale(right_shift, down_shift, multiple)
		# if a tag has children, scale them too
		if scale_children:
			for child in self.children:
				child.scale(right_shift, down_shift, multiple, scale_children)

	# A function to build the XML tree for output
	def build_et(self, et_parent=None):
		# build node and add to parent
		if et_parent is not None:
			et = ET.SubElement(et_parent, self.tag_name)
		else:
			et = ET.Element(self.tag_name)
		# add regular attributes
		for k in self.attrs:
			val = ' '.join([str(x) for x in self.attrs[k]]) if type(self.attrs[k]) == list else str(self.attrs[k])
			et.set(k, val)
		# add title attributes
		et.set('title', '; '.join([str(x) for x in self.title.values()]))
		# add text to tag
		et.text = self.text
		# add children to et tree
		for c in self.children:
			c.build_et(et)
		return et

	def get_all_subtags(self):
		output = []
		for c in self.children:
			output.append(c)
			output += c.get_all_subtags()
		return output

	# functions to find all lines or words in a document
	def find_all(self, condition=None):
		return [c for c in self.get_all_subtags() if condition(c)]

	def find_all_lines(self):
		return self.find_all(lambda c: 'ocr_line' in c.attrs.get('class', []))

	# function to set id accross frames
	def set_global_id(self, global_id):
		self.attrs['global_id'] = global_id

	# a function used by pair_with_eyes
	def get_distance(self, x, y):
		x_distance = min(abs(self.title['bbox'].left - x), abs(self.title['bbox'].right - x))
		y_distance = min(abs(self.title['bbox'].top - y), abs(self.title['bbox'].bottom - y))
		return (x_distance ** 2 + y_distance ** 2) ** .5

	# a function to connect any node to the document root
	def get_root(self):
		if self.parent is None:
			return self
		return self.parent.get_root()

	def save(self, filepath):
		et = self.build_et()
		tree = ET.ElementTree(et)
		tree.write(filepath, encoding='utf-8')
