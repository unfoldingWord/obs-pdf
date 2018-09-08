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
# docker build -t obs-pdf - < Dockerfile
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
docker run --name obs-pdf --rm -p 8080:80 -i -t obs-pdf bash
exit
```

### Run the Docker container in background and execute commands
```bash
docker pull phopper/obs-pdf:latest
docker run --name obs-pdf --rm -p 8080:80 -dit --cpus=0.5 phopper/obs-pdf:latest
docker run --name obs-pdf -p 8080:80 -dit --cpus=0.5 --restart unless-stopped phopper/obs-pdf:latest

# simple commands
docker exec obs-pdf pwd

# chained or piped commands
docker exec obs-pdf sh -c "echo 'hello' > hello.txt"

# copy a file
docker cp obs-pdf:/opt/hello.txt ~/Desktop/hello.txt

# stop the container
docker stop obs-pdf
```

### Remove a container and its image
```bash
docker rm -v 840cbddced04
docker rmi obs-pdf
```

### Remove all containers and images
```bash
# Delete all containers
docker rm $(docker ps -a -q)

# Delete all images
docker rmi $(docker images -q)
```
