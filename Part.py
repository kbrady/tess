from BBox import BBox

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