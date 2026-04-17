#!/bin/bash
# Mettre a jour les fichiers
git pull

# Selectionner la version a deployer
read -p "Version à déployer : " NOUVELLE_VERSION

# Mettre à jour la variable dans le .env
sed -i "s/^VERSION=.*/VERSION=$NOUVELLE_VERSION/" .env

# Mettre à jour le tag de l'image dans k3s-stack.yaml
sed -i "s|image: ghcr.io/zibraltar-xix/alternance-tah-les-fous:.*|image: ghcr.io/zibraltar-xix/alternance-tah-les-fous:$NOUVELLE_VERSION|" k3s-stack.yaml

# Deployer la stack Docker
kubectl apply -k .