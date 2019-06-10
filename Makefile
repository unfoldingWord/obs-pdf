# Created: 2019-05-27 RJH

baseImage:
	docker build --tag unfoldingword/obs-base:latest resources/docker-obs-base/

pushBaseImage:
	docker push unfoldingword/obs-base:latest

mainImageDebug:
	docker build --file resources/docker-app/Dockerfile-debug --tag unfoldingword/obs-pdf:debug .

mainImageDev:
	docker build --file resources/docker-app/Dockerfile-developBranch --tag unfoldingword/obs-pdf:develop resources/docker-app/

mainImage:
	docker build --file resources/docker-app/Dockerfile-masterBranch --tag unfoldingword/obs-pdf:master resources/docker-app/

pushMainDevImage:
	docker push unfoldingword/obs-pdf:develop

pushMainImage:
	docker push unfoldingword/obs-pdf:master

run:
	docker run --name obs-pdf -p 8123:80 -dit --cpus=1.0 --restart unless-stopped unfoldingword/obs-pdf:master

runDev:
	docker run --name obs-pdf -p 8123:80 -dit --cpus=1.0 --restart unless-stopped unfoldingword/obs-pdf:develop
	# Then browse to http://localhost:8123/test
	#	or http://localhost:8123/?lang_code=en
	#	then http://localhost:8123/output/en/obs-en-v5.pdf

runDevDebug:
	docker run --name obs-pdf --rm -p 8123:80 -it --cpus=0.5 unfoldingword/obs-pdf:develop bash
	# Then, inside the container, run these commands to start the application:
	#	cd /
	#	./start.sh
	#
	# conTeXt logs will be in /app/obs-pdf/output (context.err and context.out)

runDebug:
	docker run --name obs-pdf -p 8123:80 -it unfoldingword/obs-pdf:debug bash
	# Then, inside the container, run these commands to start the application:
	#	cd /
	#	./start.sh
	#
	# conTeXt logs will be in /app/obs-pdf/output (context.err and context.out)
	# Also look in /tmp/obs-to-pdf/en-xxxx/make_pdf/en.log and en.tex

connectDebug:
	# This will open another terminal view of the above container
	#	that doesn't have all of the nginx logs scrolling past
	docker exec -it `docker inspect --format="{{.Id}}" obs-pdf` bash
