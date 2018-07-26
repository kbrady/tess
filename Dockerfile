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

# Install opencv based on instructions at https://www.pyimagesearch.com/2015/06/22/install-opencv-3-0-and-python-2-7-on-ubuntu/
RUN apt-get install -y build-essential cmake git pkg-config
RUN echo deb http://security.ubuntu.com/ubuntu xenial-security main >> /etc/apt/sources.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 40976EAF437D05B5
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 3B4FE6ACC0B21F32
RUN apt update
# RUN apt-get install -y libjpeg62-turbo-dev libtiff5=4.0.6-1ubuntu0.4
# RUN apt-get install -y libtiff5-dev libjasper-dev libpng12-dev
# RUN apt-get install -y libgtk2.0-dev
RUN apt-get install -y libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
RUN apt-get install -y libatlas-base-dev gfortran

WORKDIR /
RUN git clone https://github.com/Itseez/opencv.git
WORKDIR /opencv
RUN git checkout 3.4.0

WORKDIR /
RUN git clone https://github.com/Itseez/opencv_contrib.git
WORKDIR /opencv_contrib
RUN git checkout 3.4.0

WORKDIR /opencv
RUN mkdir build
WORKDIR /opencv/build
RUN cmake -D CMAKE_BUILD_TYPE=RELEASE \
	-D CMAKE_INSTALL_PREFIX=/usr/local \
	-D INSTALL_C_EXAMPLES=ON \
	-D INSTALL_PYTHON_EXAMPLES=ON \
	-D OPENCV_EXTRA_MODULES_PATH=/opencv_contrib/modules \
	-D BUILD_EXAMPLES=ON ..
RUN make -j4
RUN make install
RUN ldconfig

WORKDIR /tess
ENTRYPOINT ["/bin/bash"]
