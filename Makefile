# Created: 2019-05-27 RJH

baseContainer:
    docker build --tag unfoldingword/obs-base:latest resources/docker-obs-base/

pushBaseImage:
	docker push unfoldingword/obs-base:latest

# composeMainContainer:
# 	docker-compose --file resources/docker-app/WhereIsYamlFile build
mainContainer:
    docker build --tag unfoldingword/obs-pdf:latest resources/docker-app/

pushMainImage:
	docker push unfoldingword/obs-pdf:latest

# From Door43 enqueue
# imageDev:
# 	# NOTE: This build sets the prefix to 'dev-' and sets debug mode
# 	docker build --file enqueue/Dockerfile-developBranch --tag unfoldingword/door43_enqueue_job:develop enqueue

# imageMaster:
# 	docker build --file enqueue/Dockerfile-masterBranch --tag unfoldingword/door43_enqueue_job:master enqueue

# pushDevImage:
# 	# Expects to be already logged into Docker, i.e., docker login -u $(DOCKER_USERNAME)
# 	docker push unfoldingword/door43_enqueue_job:develop

# pushMasterImage:
# 	# Expects to be already logged into Docker, i.e., docker login -u $(DOCKER_USERNAME)
# 	docker push unfoldingword/door43_enqueue_job:master
