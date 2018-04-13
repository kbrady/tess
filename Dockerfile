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

ENTRYPOINT ["/bin/bash"]
