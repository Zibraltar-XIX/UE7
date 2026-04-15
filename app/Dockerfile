FROM python:3.14-slim AS build

# Dossier de l'app python
WORKDIR /app

# Création de l'utilisateur non root app
RUN useradd --shell /bin/bash app

# Copier les fichiers de l'app dans le conteneur
COPY --chown=app:app ./site ./site
COPY --chown=app:app ./python ./python

# Exposer le port de l'app python
EXPOSE 5000

# Installer les dépendances
RUN pip install --no-cache-dir -r ./python/requirements.txt

# Utiliser un utilisateur non root
USER app

# Lancer l'application
CMD ["python", "./python/app.py"]