# Eye Tracker Pipeline

This is a pipeline for post processing eye tracker data on students reading from a webpage. I am writing it for studies we are doing at Vanderbilt where the eye tracking software gives us a csv with the x and y positions of a student's eyes on the screen and a video.

## Modules

### settings.py
Set the paths to directories for each part of the data. These should all be outside of the repository for real data to protect study subjects (we may add some dummy data to the repository in the future).

### video_to_frames.py
Screen grab video -> frame images

Currently finding macro transitions and transitions for the digital readings takes 3:08 per session.

### initial_ocr.py
Resize frame images so characters are 20 pixels tall
Frame images -> .hocr files via Tesseract

Running Tesseract takes longer than any other part of this process. An important goal should be decreasing the number of times we run it (currently more than once a second for the digital reading).

Questions:
- Do we want to split the screen in half during the post test when the students are shown a split screen?

### ocr_cleanup.py
.hocr files -> .xml files which have been cleaned using the stimuli files

Initially I am assuming that we have a text file for the stimuli with the correct line breaks and that students don't resize the web page during the experiment.

This process currently takes almost an hour and 48 minutes per session with digital reading. Tessaract is defenatly taking up most of that time. On average each session with a digital reading component has 144 images associated with that reading. Our goal should be to not run tesseract on all of them.

### pair_screen_with_eyes.py
.xml files -> .csv file with the distances from the x and y observed by the eye tracker to the words in the document (as displayed on the screen).

### visualize_single_page.py
Make a video of a student reading a page a web page with the scrolling taken out (maybe have a sidebar showing where the current window is)
