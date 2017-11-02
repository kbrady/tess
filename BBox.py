# a class to store, interpret and scale bounding boxes
class BBox:
	def __init__(self, info):
		if type(info) == str or type(info) == unicode:
			info = [int(x) for x in info.split(' ')]
		try:
			self.left, self.top, self.right, self.bottom = info
		except Exception as e:
			print type(info)
			print info
			raise e

	def __str__(self):
		def get_pair(attr_name):
			return attr_name+': '+str(getattr(self, attr_name))
		return ' '.join([get_pair(x) for x in ['right', 'top', 'left', 'bottom']])

	def scale(self, right_shift, down_shift, multiple):
		# stretch by multiple
		self.right *= multiple
		self.left *= multiple
		self.top *= multiple
		self.bottom *= multiple
		# shift right and left by right_shift
		self.right += right_shift
		self.left += right_shift
		# shift top and bottom by down shift
		self.top += down_shift
		self.bottom += down_shift
		# update xml object
		self.set_et(self.et)

	def set_et(self, et):
		# save this so updates can automatically happen after scaling
		self.et = et
		et.set('left', str(self.left))
		et.set('right', str(self.right))
		et.set('top', str(self.top))
		et.set('bottom', str(self.bottom))