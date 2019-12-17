master:
[![Build Status](https://travis-ci.org/unfoldingWord-dev/obs-pdf.svg?branch=master)](https://travis-ci.org/unfoldingWord-dev/obs-pdf?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/unfoldingWord-dev/obs-pdf/badge.svg?branch=master)](https://coveralls.io/github/unfoldingWord-dev/obs-pdf?branch=master)

develop:
[![Build Status](https://travis-ci.org/unfoldingWord-dev/obs-pdf.svg?branch=develop)](https://travis-ci.org/unfoldingWord-dev/obs-pdf?branch=develop)
[![Coverage Status](https://coveralls.io/repos/github/unfoldingWord-dev/obs-pdf/badge.svg?branch=develop)](https://coveralls.io/github/unfoldingWord-dev/obs-pdf?branch=develop)

# PDF Generator for OBS

#### NOTE: Python 3 Only

#### NOTE: This project is designed so that it can generate a Docker container which serves the application using Nginx.

The Flask app has 2 endpoints:

* `/test` which serves a simple test page
* `/?lang_code=xx` which attempts to generate an OBS PDF file for the requested language code (xx). If successful the client is redirected to the PDF file. If not successful, the client will receive a detailed description of the problem.


## Container Structure

The docker container was split into 2 so that the Python code could be updated without requiring the large number of image files to be updated also. This greatly reduced the time required to build and deploy the container.


## Running on AWS EC2

#### Production
The smallest EC2 instance I was able to get it to run on successfully is `t3.small`. Anything less that that would lock up consistently.

This is the command line used to start the Docker container on the EC2 instance:
```bash
docker run --name obs-pdf -p 8080:80 -dit --cpus=1.0 --restart unless-stopped unfoldingWord/obs-pdf:latest
```

#### Debugging
For testing and debugging, start the Docker container with this command:
```bash
docker run --name obs-pdf --rm -p 8080:80 -it --cpus=0.5 unfoldingWord/obs-pdf:latest bash
```

Then, inside the container, run these commands to start the application:
```bash
cd /
./start.sh
```
