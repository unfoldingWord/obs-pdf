FROM ubuntu:18.04

MAINTAINER DSM

RUN apt-get update && \
    apt-get install -y apt-utils

RUN apt-get update && \
    apt-get install -y git unzip bzip2 libfontconfig1 curl

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        haskell-platform \
        pandoc \
        pandoc-citeproc \
        texlive \
        python3-pandocfilters \
        libghc-pandoc-doc \
        libghc-pandoc-dev \
        fonts-noto \
    && apt-get autoremove -y

RUN curl -sL https://deb.nodesource.com/setup_10.x -o nodesource_setup.sh
RUN chmod +x nodesource_setup.sh
RUN ./nodesource_setup.sh
RUN apt-get install -y nodejs

RUN apt-get install -y context

RUN mkdir -p /opt/obs/images
RUN mkdir -p /opt/obs/png
RUN mkdir -p /opt/obs/jpg
RUN curl -sL https://cdn.unfoldingword.org/obs/jpg/obs-images-360px.zip -o /opt/obs/jpg/obs-images-360px.zip
RUN curl -sL https://unfoldingword.org/assets/img/uW-Level-1-128px.png -o /opt/obs/png/uW-Level-1-128px.png
RUN curl -sL https://unfoldingword.org/assets/img/uW-Level-2-128px.png -o /opt/obs/png/uW-Level-2-128px.png
RUN curl -sL https://unfoldingword.org/assets/img/uW-Level-3-128px.png -o /opt/obs/png/uW-Level-3-128px.png
RUN curl -sL https://cdn.door43.org/obs/jpg/uWOBSverticallogo1200w.png -o /opt/obs/png/uWOBSverticallogo1200w.png
RUN curl -sL https://cdn.door43.org/obs/jpg/uWOBSverticallogo600w.png -o /opt/obs/png/uWOBSverticallogo600w.png
RUN unzip /opt/obs/jpg/obs-images-360px.zip -d /opt/obs/jpg
