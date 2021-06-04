import os
from scipy.spatial import distance
import cv2
import numpy as np


# from pdf_plumber import ocr

# blank_image = 255*np.ones(shape=[500, 500], dtype=np.uint8)

# cv2.imshow('img', blank_image)

# cv2.waitKey()



# black_image = cv2.rectangle(blank_image, (0,0), (100,100), (0), -1)

# # total = np.count_zero(black_image)
# cv2.imshow('img', black_image)

# cv2.waitKey()

# blank_image_2 = 255*np.ones(shape=[500, 500], dtype=np.uint8)

# black_image_2 = cv2.rectangle(blank_image_2, (50,50), (150,150), (0), -1)

# cv2.imshow('img1', black_image_2)

# cv2.waitKey()

# black_image = cv2.bitwise_not(black_image)
# black_image_2 = cv2.bitwise_not(black_image_2)


# image_3 = cv2.bitwise_and(black_image, black_image_2)
# image_4 = cv2.bitwise_or(black_image, black_image_2)

# # image_3 = cv2.bitwise_not(image_3)

# # area = cv2.contourArea(image_3)
# # print(area)

# match = np.count_nonzero(image_3)
# total = np.count_nonzero(image_4)

# print((match/total)*100)

# cv2.imshow('img2', image_3)

# cv2.waitKey()

def match_box(ocr1, ocr2, template, test_template, idx):
	black_image = 255*np.ones(shape=[700, 1000], dtype=np.uint8)
	black_image_2 = 255*np.ones(shape=[700, 1000], dtype=np.uint8)

	for data in ocr1:
		(t,l,r,b) = (int(data['top']), int(data['left']), int(data['right']), int(data['bottom']))

		black_image = cv2.rectangle(black_image, (l,t), (r, b), (0), -1)

	for data in ocr2:
		(t,l,r,b) = (int(data['top']), int(data['left']), int(data['right']), int(data['bottom']))

		black_image_2 = cv2.rectangle(black_image_2, (l,t), (r, b), (0), -1)

	black_image = cv2.bitwise_not(black_image)
	black_image_2 = cv2.bitwise_not(black_image_2)


	file = '/home/akshat/program/aankho_dekhi/' + str(template) + '.png'
	file_1 = '/home/akshat/program/aankho_dekhi/' + test_template + str(idx) + '.png'

	# cv2.imwrite(file , black_image)
	# cv2.imwrite(file_1, black_image_2)


	image_3 = cv2.bitwise_and(black_image, black_image_2)
	image_4 = cv2.bitwise_or(black_image, black_image_2)

	file_2 = '/home/akshat/program/aankho_dekhi/' + test_template  + str(idx) + 'match.png'	
	# cv2.imwrite(file_2, image_3)

	match = np.count_nonzero(image_3)
	total = np.count_nonzero(black_image)

	if total:
		return (match/total)*100
	else:
		return 0


