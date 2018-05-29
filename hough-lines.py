import cv2
import math

img = cv2.imread("tests/four-frames/original-pictures/doc-2-sidebar-small.png")
for i in range(3):
	gray = img[:,:,i]
	edges = cv2.Canny(gray, 5, 10)
	cv2.imwrite('edges-{0}.png'.format(i), edges)
	lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi/2, threshold=300, lines=None, minLineLength=20, maxLineGap=3)
	for i in range(lines.shape[0]):
		line = lines[i,:,:].flatten()
		pt1 = (line[0],line[1])
		pt2 = (line[2],line[3])
		cv2.line(img, pt1, pt2, (0,0,255), 3)
cv2.imwrite("tmp.png", img)