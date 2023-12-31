pip freeze > requirements.txt
docker build -t esstomqtt -f Dockerfile .
docker tag esstomqtt:latest docker.diskstation/esstomqtt
docker push docker.diskstation/esstomqtt:latest