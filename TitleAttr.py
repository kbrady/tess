class TitleAttr(object):
	def __init__(self, name, values):
		self.name = name
		self.values = [x for x in values.split(' ')]

	def __repr__(self):
		return self.name + ' ' + ' '.join([str(x) for x in self.values])