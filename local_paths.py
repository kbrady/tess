# some things to import for the tagging functions
import numpy as np
from scipy import misc

# set paths, raw_dir should not end with a file seperator, but data_dir should
raw_dir = '/videos'
data_dir = '/tess/data/'

# highlight colors
highlight_colors = {
	'dark blue':(71,148,241),
	'yellow':(253, 250, 193),
	'light blue':(213, 242, 254),
	'white':(245, 245, 245),
	'black':(10,10,10)}
highlight_viz_colors = highlight_colors.copy()
highlight_viz_colors['white'] = (255, 255, 255)
highlight_color_pairs = {
	'dark blue': (highlight_colors['white'], highlight_colors['dark blue']),
	'light blue':(highlight_colors['light blue'], highlight_colors['black']),
	'yellow':(highlight_colors['yellow'], highlight_colors['black']),
	'white':(highlight_colors['white'], highlight_colors['black'])
}
# def avg(x):
# 	return sum([v for v in x])/len(x)

# highlight_colors = {
#   'white':(255, 255, 255),
#   'black':(0,0,0),
#   'yellow':(244, 174, 77),
#   'light blue':(213, 242, 254),
#   'purple':(73,112,210),
#   'red':(255,0,0),
#   'green':(0,255,0),
#   'blue':(0,0,255)
# }
# highlight_viz_colors = highlight_colors.copy()

# highlight_color_pairs = {}
# for c1 in highlight_colors:
# 	for c2 in highlight_colors:
# 		if avg(highlight_colors[c1]) >= avg(highlight_colors[c2]):
# 			continue
# 		highlight_color_pairs[c1+' and '+c2] = (highlight_colors[c1], highlight_colors[c2])

# edittor to use
editor_dir = 'Kate_edits'

# # values for splitting videos
big_t = 1
little_t = .1

# functions for disecting videos
# need to fix this function
def figure_out_part_of_stimuli_frame_is_in(image_path):
	return 'digital reading'
	pic = np.array(misc.imread(image_path))
	# cut off the top and bottom parts of the frame which show the address bar and the dock
	# cut off the right part of the frame which may be showing the note taking menu (not important for the moment)
	pic = pic[50:800, :900, :]
	if is_form(pic):
		return 'form'
	else:
		percent_white = image_has_color(pic, rgb=[255, 255, 255])
		if percent_white > .8:
			return 'paper or splash page'
		elif percent_white > .4:
			return 'digital reading'
		else:
			return 'nothing'

# this is used to identify which part of the webpage a frame belongs to
# In our studies, the google form pages all had a puruple header which was not present in other pages
def image_has_color(pic, threashold=None, rgb=[237, 230, 246], upper_threashold=None, epsilon=0):
	difference_from_color = abs(pic[:,:,0] - rgb[0]) + abs(pic[:,:,1] - rgb[1]) + abs(pic[:,:,2] - rgb[2])
	num_pixels = sum(sum(difference_from_color <= epsilon))
	# if no threashold is given return the percentage of pixels that had the specified color
	if threashold is None:
		height, width, depth = pic.shape
		return float(num_pixels)/(height*width)
	# otherwise return a binary value based on the threasholds
	if upper_threashold is None:
		return num_pixels > threashold
	else:
		return (num_pixels > threashold) and (num_pixels < upper_threashold)

def is_form(pic):
	# only the forms had any purple in them
	# however some may have purple which is off by an rgb value so we take this into effect
	# forms should have about 10000 of these pixels at the top
	if image_has_color(pic, 10000, rgb=[237, 230, 246], epsilon=0):
		return True
	# sometimes the form side goes white while loading the next question
	pic_left = pic[100:600, :600, :]
	if not image_has_color(pic_left, rgb=[255, 255, 255]) > .99:
		return False
	# the other side should have text
	# we have already estabilshed that the left side is only white pixels, so 
	# any non-white pixels on the right side tells us we're looking at a page that isn't all white
	# thus this must be part of the form
	pic_right = pic[100:600, 700:, :]
	percent_white_on_right_side = image_has_color(pic_right, rgb=[255, 255, 255])
	return percent_white_on_right_side < .98