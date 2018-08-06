FROM ubuntu:18.04

MAINTAINER DSM

RUN apt-get update \
    && apt-get install -y apt-utils

RUN apt-get update \
    && apt-get install -y \
        git unzip \
        bzip2 \
        libfontconfig1 \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        haskell-platform \
        pandoc \
        pandoc-citeproc \
        texlive \
        python3-pandocfilters \
        libghc-pandoc-doc \
        libghc-pandoc-dev \
        fonts-noto \
        context \
    && apt-get autoremove -y

RUN curl -sL https://deb.nodesource.com/setup_10.x -o nodesource_setup.sh \
    && chmod +x nodesource_setup.sh \
    && ./nodesource_setup.sh

RUN apt-get install -y nodejs

RUN pip3 install -U Flask

RUN mkdir -p /opt/obs/images \
    && mkdir -p /opt/obs/png \
    && mkdir -p /opt/obs/jpg \
    && curl -sL https://cdn.unfoldingword.org/obs/jpg/obs-images-360px.zip -o /opt/obs/jpg/obs-images-360px.zip \
    && curl -sL https://unfoldingword.org/assets/img/uW-Level-1-128px.png -o /opt/obs/png/uW-Level-1-128px.png \
    && curl -sL https://unfoldingword.org/assets/img/uW-Level-2-128px.png -o /opt/obs/png/uW-Level-2-128px.png \
    && curl -sL https://unfoldingword.org/assets/img/uW-Level-3-128px.png -o /opt/obs/png/uW-Level-3-128px.png \
    && curl -sL https://cdn.door43.org/obs/jpg/uWOBSverticallogo1200w.png -o /opt/obs/png/uWOBSverticallogo1200w.png \
    && curl -sL https://cdn.door43.org/obs/jpg/uWOBSverticallogo600w.png -o /opt/obs/png/uWOBSverticallogo600w.png \
    && unzip /opt/obs/jpg/obs-images-360px.zip -d /opt/obs/jpg
