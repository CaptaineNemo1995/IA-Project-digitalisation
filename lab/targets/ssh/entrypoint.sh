#!/bin/sh
set -e

# Clés d'hôte SSH (si absentes)
ssh-keygen -A

# Utilisateur de test créé à partir des variables du .env
id "$SSH_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$SSH_USER"
echo "$SSH_USER:$SSH_PASSWORD" | chpasswd

# -D : premier plan ; -e : journaux d'authentification vers la sortie standard (docker logs)
exec /usr/sbin/sshd -D -e
