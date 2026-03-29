#!/bin/sh

ssh -o StrictHostKeyChecking=no -p $PORT $USER@$DOMAIN << 'ENDSSH'
  cd ~/porfacan/
  export $(cat .env | xargs)
  echo $CI_JOB_TOKEN | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
  docker pull $APP_IMAGE
  docker pull $PROXY_IMAGE
  docker compose -f docker-compose.prod.yml up --build -d
  if docker ps -a --format '{{.Names}}' | grep -q '^porfacan-web$'; then
    docker restart porfacan-web
  fi
  rm .env
ENDSSH