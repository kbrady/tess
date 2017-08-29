from BBox import BBox
# to write corrected output to file
import xml.etree.cElementTree as ET

# A parent object for lines and words which defines some shared functionality
class Part(object):
	def __init__(self, tag):
		info = tag['title'].split('; ')
		self.bbox = BBox(info[0][info[0].find(' ')+1:])
		self.id = tag['id']

	def width(self):
		return self.bbox.right - self.bbox.left

	def height(self):
		return self.bbox.bottom - self.bbox.top

	# make an element tree object to save everything as xml
	def set_et(self, et_parent, tag_name):
		# et_parent will be None if this is a top level tag
		# In practice this is never since neither lines nor words are top level
		if et_parent is not None:
			self.et = ET.SubElement(et_parent, tag_name)
		else:
			self.et = ET.Element(tag_name)
		# set attributes of this tag like id and dimensions
		# we will use the id to audit for accuracy
		self.et.set('id', self.id)
		self.bbox.set_et(self.et)