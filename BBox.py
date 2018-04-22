from TitleAttr import TitleAttr

# a class to store, interpret and scale bounding boxes
class BBox(TitleAttr):
	def __init__(self, name, values):
		super(self.__class__, self).__init__(name, values)
		self.left, self.top, self.right, self.bottom = [float(x) for x in self.values]

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
		self.values = [self.left, self.top, self.right, self.bottom]