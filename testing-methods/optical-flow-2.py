import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import namedtuple, Counter
import os

# # helper functon to do a recursive search and find boxes around
# # we only need to find one box to consider images different, so
# # don't worry about figuring out where they are
# def find_boxes(mag, ang, depth=0):
# 	# important constants based on search of best values for
# 	# splitting the images found for the seventh undergrad
# 	frac_for_diff = .9
# 	cutoff = 1
# 	# get the dimensions of the matrix part
# 	height, width = mat.shape
# 	# figure out if the stoping consitions are met
# 	num_above_cutoff = (mat > cutoff).sum()
# 	if float(num_above_cutoff)/mat.size > frac_for_diff:
# 		return True
# 	# if a box has less than 100 * frac_for_diff pixels which are different
# 	# it couldn't be mostly different anyway
# 	if num_above_cutoff.sum() < 100 * frac_for_diff:
# 		return False
# 	# if the size falls bellow double the height of text, we don't consider smaller windows
# 	if height < 20 and width < 20:
# 		return False
# 	# split mat in half
# 	mat_l = mat[:, :width/2]
# 	mat_r = mat[:, width/2:]
# 	# get results
# 	# transpose the matrix so next time we cut top to bottom
# 	left_diff = find_box(mat_l.T, depth + 1)
# 	# if we found a box on the left, don't bother looking on the right
# 	if left_diff:
# 		return left_diff
# 	right_diff = find_box(mat_r.T, depth + 1)
# 	return right_diff

# def divide_vectors(mag, ang, epsilon=1, max_ang_diff=np.pi/20, max_mag_diff=4):


def get_polar_flow(gray1, gray2):
	flow = cv2.calcOpticalFlowFarneback(gray1, gray2, flow=None, pyr_scale=0.5, levels=3, winsize=15, iterations=3, poly_n=5, poly_sigma=1.2, flags=0) 
	mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1])
	vectors = []
	Vec = namedtuple('Vec', 'mag ang x y')
	epsilon = 1
	for x in range(flow.shape[0]):
		for y in range(flow.shape[1]):
			if mag[x,y] > epsilon:
				vectors.append(Vec(mag, ang, x, y))
	plt.hist(ang.flatten())
	plt.savefig('ang.jpg')
	plt.close()
	mag_counter = Counter([round(x,2) for x in mag.flatten()])
	values = list(mag_counter.keys())
	values.sort()
	for k in values:
		print '{0:.2f}: {1}'.format(k, mag_counter[k])
	print(len([x for x in list(mag.flatten()) if (x > epsilon) and (x < 1000)]))
	plt.hist([x for x in list(mag.flatten()) if (x > epsilon) and (x < 1000)])
	plt.savefig('mag.jpg')
	plt.close()
	return mag, ang

def get_frames_from_video(video_path, output_dir, start_frame=0, last_frame=None):
	cap = cv2.VideoCapture(video_path)
	ret, frame1 = cap.read()
	prvs = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)
	counter = 0
	while(1):
		ret, frame2 = cap.read()
		next = cv2.cvtColor(frame2,cv2.COLOR_BGR2GRAY)
		if counter < start_frame:
			prvs = next
			counter += 1
			continue
		#get_polar_flow(prvs, next)
		flow = cv2.calcOpticalFlowFarneback(prvs,next, flow=None, pyr_scale=0.5, levels=3, winsize=15, iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
		U = flow[...,0]
		V = flow[...,1]
		# down sample to get a reasonably sized vector field
		num = 30
		U = U[::num, ::num]/(num**2)
		V = V[::num, ::num]/(num**2)

		plt.figure()
		plt.imshow(frame2)
		X = []
		Y = []
		for i in range(frame2.shape[0]):
			if i % num == 0:
				for j in range(frame2.shape[1]):
					if j % num == 0:
						X.append(j)
						Y.append(i)
		plt.title('flow-{0}'.format(counter))
		Q = plt.quiver(X, Y, U, V)
		plt.savefig(output_dir+'/frame-{0}.jpg'.format(counter), dpi=300)
		plt.close()

		# ending conditions
		k = cv2.waitKey(1)
		if k == 27:
			break

		# iterate frames and counters
		prvs = next
		counter += 1

		# just want to go through a few times
		if last_frame is not None and counter > last_frame:
			break
	cap.release()
	cv2.destroyAllWindows()

def get_optical_flow_from_images(input_dir, output_dir):
	input_dir = input_dir if input_dir[-1] == os.sep else input_dir + os.sep
	output_dir = output_dir if output_dir[-1] == os.sep else output_dir + os.sep
	images = list(os.listdir(input_dir))
	images.sort()
	images = [input_dir + x for x in images if not x.startswith('.')]
	print(images[:10])
	frame1 = cv2.imread(images[0])
	print(frame1.shape)
	prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
	counter = 0
	for image_path in images[1:]:
		frame2 = cv2.imread(image_path)
		next = cv2.cvtColor(frame2,cv2.COLOR_BGR2GRAY)
		flow = cv2.calcOpticalFlowFarneback(prvs, next, flow=None, pyr_scale=0.5, levels=3, winsize=15, iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
		U = flow[...,0]
		V = flow[...,1]
		# down sample to get a reasonably sized vector field
		num = 30
		U = U[::num, ::num]/(num**2)
		V = V[::num, ::num]/(num**2)

		plt.figure()
		plt.imshow(frame2)
		X = []
		Y = []
		for i in range(frame2.shape[0]):
			if i % num == 0:
				for j in range(frame2.shape[1]):
					if j % num == 0:
						X.append(j)
						Y.append(i)
		plt.title(image_path.split(os.sep)[-1])
		Q = plt.quiver(X, Y, U, V)
		plt.savefig(output_dir+image_path.split(os.sep)[-1], dpi=300)
		plt.close()

		# iterate frames and counters
		prvs = next
		counter += 1
	cv2.destroyAllWindows()

get_optical_flow_from_images('../data/resized-images', '../data/flow-images')