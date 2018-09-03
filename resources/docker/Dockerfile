FROM tiangolo/uwsgi-nginx-flask:python3.6

MAINTAINER DSM

# Which uWSGI .ini file should be used, to make it customizable
ENV UWSGI_INI /app/obs-pdf/public/uwsgi.ini

# install apt-utils so the rest of the install goes more smoothly
RUN apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get install -y apt-utils

# install packages
RUN apt-get update \
    && apt-get install -y \
        git unzip \
        bzip2 \
        libfontconfig1 \
        curl \
        haskell-platform \
        pandoc \
        pandoc-citeproc \
        texlive \
        python3-pandocfilters \
        libghc-pandoc-doc \
        libghc-pandoc-dev \
        fonts-noto \
        context \
        wget \
        nano \
    && apt-get autoremove -y

# install nodejs
RUN curl -sL https://deb.nodesource.com/setup_10.x -o nodesource_setup.sh \
    && chmod +x nodesource_setup.sh \
    && ./nodesource_setup.sh \
    && apt-get install -y nodejs

# download images for OBS
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

# install the obs-pdf app
RUN cd /app && git clone --single-branch -b develop https://github.com/unfoldingWord-dev/obs-pdf.git \
    && cd /app/obs-pdf \
    && git pull \
    && pip install --upgrade pip \
    && pip install --upgrade -r prerequisites.txt \
    && pip install -r requirements.txt

COPY start.sh /start.sh
