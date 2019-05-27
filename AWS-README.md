# Configuring AWS EC2

Adapted from: https://www.ybrikman.com/writing/2015/11/11/running-docker-aws-ground-up/

```bash
sudo amazon-linux-extras install docker
sudo service docker start
sudo usermod -a -G docker ec2-user
exit
```

```bash
docker info
docker run --name obs-pdf --rm -p 8080:80 -i -t unfoldingWord/obs-pdf:latest bash
```
