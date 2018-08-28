# Docker Container for Building OBS PDF Files

Includes Python3 and ConText


### Add yourself to the docker group
```bash
sudo usermod -a -G docker YOUR_USER
sudo reboot
```

### Build the Docker container
```bash
cd ~/Projects/dsm-docker
# docker build -t dcs-context - < Dockerfile
docker-compose build --force-rm
```

### Show running containers
```bash
docker container ls
```

### Show all containers, running or not
```bash
docker container ls -a
```

### Run the Docker container, opening shell
```bash
docker run --name dcs-context --rm --workdir /opt -i -t dcs-context bash
exit
```

### Run the Docker container in background and execute commands
```bash
docker run -d --name dcs-context --rm --workdir /opt -i -t dcs-context

# simple commands
docker exec dcs-context pwd

# chained or piped commands
docker exec dcs-context sh -c "echo 'hello' > hello.txt"

# copy a file
docker cp dcs-context:/opt/hello.txt ~/Desktop/hello.txt

# stop the container
docker stop dcs-context
```

### Remove a container and its image
```bash
docker rm -v 840cbddced04
docker rmi dcs-context
```

### Remove all containers and images
```bash
# Delete all containers
docker rm $(docker ps -a -q)

# Delete all images
docker rmi $(docker images -q)
```
