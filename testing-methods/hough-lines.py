import cv2
import math
import json

# calculate what the output is with given settings
def get_lines(img, rho, theta, threshold, minLineLength, maxLineGap):
	output = []
	for i in range(3):
		gray = img[:,:,i]
		edges = cv2.Canny(gray, 5, 10)
		lines = cv2.HoughLinesP(edges, rho=rho, theta=theta, threshold=threshold, lines=None, minLineLength=minLineLength, maxLineGap=maxLineGap)
		for i in range(lines.shape[0]):
			line = lines[i,:,:].flatten()
			output.append(((line[0], line[2]), (line[1], line[3])))
	return output

def get_distance(line_1, line_2):
	# measure distance as cosine similarity plus distance to endpoints
	width = lambda l: abs(l[0][0] - l[0][1])
	height = lambda l: abs(l[1][0] - l[1][1])
	length = lambda l: math.sqrt(width(l) ** 2 + height(l) ** 2)
	cos_sim = (width(line_1) * width(line_2) + height(line_1) * height(line_2))/(length(line_1) * length(line_2))
	cos_distance = 1 - cos_sim
	if cos_distance > .3:
		return 10000000
	# distance to endpoint should be more important because cos_distance should always be about 0
	point_fun = lambda p_1, p_2: math.sqrt((p_1[0] - p_2[0]) ** 2 + (p_1[1] - p_2[1]) ** 2)
	point_distance = point_fun((line_1[0][0], line_1[1][0]), (line_2[0][0], line_2[1][0]))
	point_distance += point_fun((line_1[0][1], line_1[1][1]), (line_2[0][1], line_2[1][1]))
	return point_distance


# find the closest line in correct_lines
# use cosei
def closest_line(line, correct_lines):
	point_1 = (line[0][0], line[1][0])
	point_2 = (line[0][1], line[1][1])
	# the line is horizontal if the y values are the same
	is_horizontal = point_1[1] == point_2[1]
	best_match = None
	best_score = None
	for l in correct_lines:
		dist = get_distance(line, l)
		if best_match is None or dist < best_score:
			best_score = dist
			best_match = l
	return best_match, best_score

# check if a line should be ignored because the correct lines haven't been categorized for that region
def ignore_line(line):
	point_1 = (line[0][0], line[1][0])
	point_2 = (line[0][1], line[1][1])
	if point_1[1] <= 78 or point_2[1]<= 78:
		return True
	return False

# get how far off the assignment is from the correct assignment
def get_assignment_distance(correct_lines, lines):
	matched = []
	total_distance = 0
	for l in lines:
		if ignore_line(l):
			continue
		matched_line, score = closest_line(l, correct_lines)
		matched.append(matched_line)
		total_distance += score
	for l in correct_lines:
		if l in matched:
			continue
		else:
			total_distance += 10000

def draw_lines(lines, img, filename):
	img = img.copy()
	for line in lines:
		pt1 = (line[0][0], line[1][0])
		pt2 = (line[0][1], line[1][1])
		cv2.line(img, pt1, pt2, (0,0,255), 3)
	cv2.imwrite(filename, img)

img = cv2.imread("data/video6/frame-images/00-10.3.jpg")
# read in the correct lines
with open('data/video6/correct_lines.json', 'r') as input_file:
    filename_lines_pair = json.loads(' '.join([line for line in input_file]))
correct_lines = filename_lines_pair['00-10.3.jpg']
# change the type of correct lines from lists to tuples so lines can be hashed
correct_lines = [tuple((tuple(x[0]), tuple(x[1]))) for x in correct_lines]
# set a starting learning rate and values for hill climbing
learning_rate = 1
parameters_list = ['rho', 'theta', 'threshold', 'minLineLength', 'maxLineGap']
parameters = {'rho': 1, 'theta':math.pi/2, 'threshold':2, 'minLineLength':30, 'maxLineGap':1}
steps = {}
for k in parameters_list:
	steps[k] = parameters[k]/20
# get a starting value
current_lines = get_lines(img, *[parameters[k] for k in parameters_list])
current_distance = get_assignment_distance(correct_lines, current_lines)
draw_lines(current_lines, img, 'starting_position.png')
for i in range(5):
	new_parameters = parameters
	for key in parameters_list:
		parameters_editted = parameters.copy()
		parameters_editted[key] += steps[key] * learning_rate
		if key in ['threshold']:
			parameters_editted[key] = int(parameters_editted[key])
		new_lines = get_lines(img, *[parameters_editted[k] for k in parameters_list])
		new_distance = get_assignment_distance(correct_lines, new_lines)
		if new_distance < current_distance:
			new_parameters = parameters_editted
			current_distance = new_distance
			current_lines = new_lines
		parameters_editted = parameters.copy()
		parameters_editted[key] -= steps[key] * learning_rate
		if key in ['threshold']:
			parameters_editted[key] = int(parameters_editted[key])
		new_lines = get_lines(img, *[parameters_editted[k] for k in parameters_list])
		new_distance = get_assignment_distance(correct_lines, new_lines)
		if new_distance < current_distance:
			new_parameters = parameters_editted
			current_distance = new_distance
			current_lines = new_lines
	parameters = new_parameters
	learning_rate *= learning_rate
draw_lines(current_lines, img, 'after_5_steps.png')