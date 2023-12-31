#! /bin/bash

CONTAINER_NAME=essToMqtt
REG_NAME=docker.diskstation/esstomqtt:latest
DIR_NAME=Ess2Mqtt
#CONFIG_NAME=mqtt2influx.json

docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

case "$1" in 
    "test")
        docker rmi $REG_NAME
        docker run \
#        -v /home/pi/docker/$DIR_NAME/$CONFIG_NAME:/app/$CONFIG_NAME \
        -v /etc/timezone:/etc/timezone:ro \
        -v /etc/localtime:/etc/localtime:ro \
        -e "TZ=Europe/Berlin" \
        --name $CONTAINER_NAME \
        $REG_NAME
        ;;
    "run")
        docker run -id\
#        -v /home/pi/docker/$DIR_NAME/$CONFIG_NAME:/app/$CONFIG_NAME \
        -v /etc/timezone:/etc/timezone:ro \
        -v /etc/localtime:/etc/localtime:ro \
        -e "TZ=Europe/Berlin" \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        $REG_NAME
        ;;
    *)
        echo "Invalid option. Supported options: test, run"
        exit 1
        ;;        
esac