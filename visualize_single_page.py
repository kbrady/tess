import initial_ocr
import ocr_cleanup

def images_to_xml():
	# Run tesseract on the website images
	image_dir = 'parts_for_viz'+os.sep+'resized-images'
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(image_dir):
		image_path = image_dir + os.sep + filename
		hocr_path = hocr_dir + os.sep + filename
		initial_ocr.run_tesseract_on_image(image_path, hocr_path)
	# Cleanup the tesseract output
	hocr_dir = 'parts_for_viz'+os.sep+'hocr-files'
	for filename in os.listdir(hocr_dir):
		hocr_path = hocr_dir + os.sep + filename
		cleanup_file(hocr_path, correct_bags=get_correct_bags())

