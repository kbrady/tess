# to write corrected output to file
import xml.etree.cElementTree as ET
# to read hocr files and write xml files
from bs4 import BeautifulSoup
# to build title attributes
from TitleAttr import TitleAttr
from BBox import BBox

# A master template for saving all XML type tags
class XML:
	def __init__(self, tag, parent=None):
		# read the tag and all it's attributes
		self.tag_name = tag.name
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
		# keep track of parents
		self.parent = parent
		self.children = []
		for c in tag.findChildren():
			self.children.append(XML(c, self))

	# A function to build the XML tree for output
	def buil_et(self, et_parent=None):
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, self.tag_name)
		else:
			self.et = ET.Element(self.tag_name)
		for k in self.attrs:
			self.et.set(k, self.attrs[k])
		self.et.set('title', '; '.join([str(x) for x in self.title.values()]))
		for c in self.children():
			c.build_et(self.et)
