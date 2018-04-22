FROM python:2.7

WORKDIR /tess

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install packages.
RUN apt-get update
# install ocr engine (tesseract)
RUN apt-get install -y tesseract-ocr
# and frame fetcher (ffmpeg in deb-multimedia-keyring)
RUN echo deb http://ftp.uk.debian.org/debian jessie-backports main >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get -f install -y ffmpeg

# Install opencv
RUN apt-get install -y build-essential cmake git pkg-config
RUN apt-get install -y libjpeg62-turbo-dev libtiff5-dev libjasper-dev libpng12-dev
RUN apt-get install -y libgtk2.0-dev
RUN apt-get install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
RUN apt-get install -y libatlas-base-dev gfortran

WORKDIR /
RUN git clone https://github.com/Itseez/opencv.git

WORKDIR /tess
ENTRYPOINT ["/bin/bash"]
