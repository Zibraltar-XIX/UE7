# Image docker
FROM python:3.14-slim

# Dossier de travail dans le conteneur
WORKDIR /app

# Copier les fichiers de l'app dans le conteneur
COPY ./site ./site
COPY ./python ./python

# Installer les dépendances Python
RUN pip install --no-cache-dir -r ./python/requirements.txt

# Exposer le port de l'application
EXPOSE 5000

# Lancer l'application
CMD ["python", "./python/app.py"]