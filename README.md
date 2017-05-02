# Eye Tracker Pipeline

This is a pipeline for post processing eye tracker data on students reading from a webpage. I am writing it for studies we are doing at Vanderbilt where the eye tracking software gives us a csv with the x and y positions of a student's eyes on the screen and a video.

## Modules

### settings.py
Set the paths to directories for each part of the data. These should all be outside of the repository for real data to protect study subjects (we may add some dummy data to the repository in the future).

### video_to_frames.py
Screen grab video -> frame images

### resize_frames.py
Resize frame images so characters are 20 pixels tall

### initial_ocr.py
Frame images -> .hocr files via Tesseract

Questions:
- Do we want to split the screen in half during the post test when the students are shown a split screen?

### ocr_cleanup.py
.hocr files -> .xml files which have been cleaned using the stimuli files

Initially I am assuming that we have a text file for the stimuli with the correct line breaks and that students don't resize the web page during the experiment.

### visualize_single_page.py
Make a video of a student reading a page a web page with the scrolling taken out (maybe have a sidebar showing where the current window is)