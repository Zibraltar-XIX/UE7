#!/bin/bash
# Mettre a jour les fichiers
git pull

# Selectionner la version a deployer
read -p "Version à déployer : " NOUVELLE_VERSION
sed -i "s/^VERSION=.*/VERSION=$NOUVELLE_VERSION/" .env

# Deployer la stack Docker
set -a
. ./.env
set +a
docker stack deploy --prune -c docker-stack.yml alternance-tah-les-fous
