#!/usr/bin/env bash
# CyberSentinel AI — Installation de Wazuh (étape 2)
# À lancer DANS la sandbox, depuis la racine du dépôt :  bash scripts/setup-siem.sh
set -euo pipefail

WAZUH_VERSION="v4.14.9"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/lab/siem/wazuh-docker"

# Les variables du labo ne doivent pas s'appliquer à la stack Wazuh
unset COMPOSE_FILE COMPOSE_ENV_FILES

echo "[1/5] Vérification que le labo tourne (réseau labnet requis)"
docker network inspect cybersentinel-lab_labnet >/dev/null

echo "[2/5] Récupération de Wazuh $WAZUH_VERSION"
if [ ! -d "$DEST" ]; then
  git clone --depth 1 -b "$WAZUH_VERSION" https://github.com/wazuh/wazuh-docker.git "$DEST"
fi
cp "$ROOT/lab/siem/docker-compose.override.yml" "$DEST/single-node/"

echo "[3/5] Réglage noyau requis par l'indexeur (vm.max_map_count)"
sudo sysctl -w vm.max_map_count=262144

cd "$DEST/single-node"

echo "[4/5] Génération des certificats TLS (une seule fois)"
if [ ! -f config/wazuh_indexer_ssl_certs/root-ca.pem ]; then
  docker compose -f generate-indexer-certs.yml run --rm generator
fi

echo "[5/5] Démarrage de Wazuh"
docker compose up -d

echo
echo "[+] Wazuh démarré. L'interface met 1 à 3 minutes à être prête."
echo "    État :  cd $DEST/single-node && docker compose ps"
