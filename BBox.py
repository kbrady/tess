

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
		return ' '.join([str(x) for x in [self.right, self.top, self.left, self.bottom]])

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