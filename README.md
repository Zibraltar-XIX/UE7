# Docker Swarm

**Démarrer docker swarm :** ```docker swarm init```

**Deployer la stack :** ```docker stack deploy -c docker-stack.yml alternance-tah-les-fous```

**Surveiller le déploiement :** ```docker service ps alternance-tah-les-fous```

**Voir l'état général :** ```docker service ls```

**Rollback manuel :** ```docker service rollback alternance-tah-les-fous```

**Supprimer la stack (hors volume) :** ```docker stack rm alternance-tah-les-fous```