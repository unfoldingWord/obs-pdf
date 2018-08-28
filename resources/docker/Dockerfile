FROM nginx:latest

MAINTAINER DSM

# use `bash` instead of the default `sh`,
# because we call the built-in `source` command to activate the python virtual environment
SHELL ["/bin/bash", "-c"]

# install apt-utils so the rest of the install goes more smoothly
RUN apt-get update \
    && apt-get install -y apt-utils

# install packages
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
RUN cd /opt && git clone --single-branch -b develop https://github.com/unfoldingWord-dev/obs-pdf.git \
    && cd /opt/obs-pdf \
    && git pull \
    && python3 -m venv venv \
    && source venv/bin/activate \
    && pip install --upgrade -r prerequisites.txt \
    && pip install -r requirements.txt

# configure nginx
RUN rm -f /opt/obs-pdf/backup/default.conf \
    && mv /etc/nginx/conf.d/default.conf /opt/obs-pdf/backup/default.conf \
    && ln -sf /opt/obs-pdf/config/obs-pdf.conf /etc/nginx/conf.d/obs-pdf.conf

#ENTRYPOINT ["/opt/obs-pdf/docker-entrypoint.sh"]
