#!/usr/bin/env bash
# CyberSentinel AI — Lancement de l'agent IA (étape 4)
# À lancer DANS la sandbox, depuis la racine du dépôt :  bash ai-agent/start-goose.sh
#
# - Charge la clé NVIDIA depuis .env (jamais écrite dans un fichier de config)
# - Génère la configuration Goose : modèle NVIDIA NIM + UNIQUEMENT notre serveur MCP Wazuh
#   (extension « developer » désactivée => l'agent ne peut exécuter aucune commande)
# - Démarre une session Goose en mode « approve » (validation humaine des appels d'outils)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

set -a; source "$ROOT/.env"; set +a
: "${NVIDIA_API_KEY:?Définir NVIDIA_API_KEY dans .env}"
MODEL="${NVIDIA_MODEL:-meta/llama-3.3-70b-instruct}"

command -v goose >/dev/null || export PATH="$HOME/.local/bin:$PATH"
command -v goose >/dev/null || { echo "Goose absent : voir docs/etape4-ia.md (installation)"; exit 1; }

mkdir -p "$HOME/.config/goose"
cat > "$HOME/.config/goose/config.yaml" <<EOF
GOOSE_PROVIDER: openai
GOOSE_MODEL: ${MODEL}
GOOSE_MODE: approve
OPENAI_HOST: https://integrate.api.nvidia.com
OPENAI_BASE_PATH: v1/chat/completions
extensions:
  developer:
    name: developer
    type: builtin
    enabled: false
  wazuh:
    name: wazuh
    type: stdio
    cmd: python3
    args:
      - ${ROOT}/ai-agent/wazuh_mcp.py
    enabled: true
    timeout: 60
EOF

export OPENAI_API_KEY="$NVIDIA_API_KEY"
export GOOSE_DISABLE_KEYRING=1

echo "[+] Goose : modèle ${MODEL} via NVIDIA NIM, outils = serveur MCP Wazuh (lecture seule)"
cd "$ROOT/ai-agent"      # .goosehints de ce dossier = consignes d'analyste SOC
exec goose session "$@"
