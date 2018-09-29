# Text-position Evaluation from a Screen-recorded Session (TESS)

This is a pipeline for processing screen recordings to recognize text positions, mouse movements, highlighting and navigation events. It can be used to categorize youtube videos, parse data from digital reading experiments or tag your own actions from a personal screen recording.

## Installation
This pipeline uses several software packages including Python 3.6, [https://github.com/tesseract-ocr/tesseract](Tessaract), and ffmpeg. To install all these packages and their dependencies I have build a Dockerfile.

First you will need to install Docker. You can find installation instructions for your operating system at [https://docs.docker.com/install/](this link).

If you aren't sure if docker is installed on your system, you can test by attempting to run the hello world image (you may need to add a `sudo` to the front of this command):

`docker run hello-world`

Once Docker is installed, run the following command to build the environment for TESS. If you would like to name your environment something other than tess, substatute that name after the `-t`.

`docker build -t tess .`

To enter the docker environment after building it use the following command

`docker run -it -p 5000:5000 -v $PWD:/tess -v <path-to-your-videos>:/videos tess`

## Settings
You will need a file called local_paths.py with 

path names to the directories your data is in and that generated files should be stored in.

An example can be seen in local_paths_example.py

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

This currently takes .8 seconds per session with digital reading.

### visualize_single_page.py
Make a video of a student reading a page a web page with the scrolling taken out (maybe have a sidebar showing where the current window is)
