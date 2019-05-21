sudo docker rmi $(sudo docker images -q)
sudo docker rm $(sudo docker ps -a -q)