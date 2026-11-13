# Étape 4 : Investigation assistée par IA (Goose + MCP + NVIDIA NIM)

## Objectif
Donner à un agent IA l'accès **contrôlé** aux données de sécurité, pour qu'il aide l'analyste à interpréter les alertes et à produire un rapport d'investigation, sans jamais pouvoir agir seul sur le système.

## Les trois briques

| Brique | Rôle | Choix |
|---|---|---|
| **Goose** (v1.59.0) | L'agent : dialogue avec l'analyste, décide quels outils appeler, assemble la réponse | Open source (Linux Foundation / AAIF), installé **dans la sandbox** |
| **MCP** (Model Context Protocol) | Le protocole standard qui relie l'agent à des outils externes | Serveur `ai-agent/wazuh_mcp.py`, écrit par nous, **lecture seule** |
| **NVIDIA NIM** | Le modèle de langage qui raisonne et rédige | `minimaxai/minimax-m3.1-flash`, endpoint gratuit (badge *Free Endpoint*) |

## Comment ça marche

### 1. Au lancement (`ai-agent/start-goose.sh`)
1. Le script **lit le `.env`** : `NVIDIA_API_KEY` et `NVIDIA_MODEL`.
2. Il **écrit la configuration de Goose** (`~/.config/goose/config.yaml`) :
   - fournisseur « compatible OpenAI » pointant sur `integrate.api.nvidia.com` ;
   - le modèle choisi ;
   - **un seul outil autorisé** : notre serveur `wazuh_mcp.py`. L'extension `developer` (shell, fichiers) est **désactivée**.
   - mode **`approve`** : chaque appel d'outil doit être validé par l'humain.
3. Il **passe la clé à Goose par une variable d'environnement** (`OPENAI_API_KEY`). La clé n'est jamais écrite dans un fichier de configuration, ni envoyée sur GitHub.
4. Il **démarre Goose** depuis `ai-agent/`, où le fichier `.goosehints` lui donne ses consignes d'analyste SOC.

### 2. Quand on pose une question
```
Analyste : « Rapport sur les alertes SSH »
   │
   ▼
Goose ──(question + liste des 4 outils)──► Modèle MiniMax (chez NVIDIA)
   │                                              │
   │         ◄── « appelle resume_alertes(24h) » ─┘
   │
   ├─ demande la validation à l'analyste (mode approve)
   ▼
wazuh_mcp.py ──(lecture seule)──► indexeur Wazuh ──► alertes
   │
   ▼
Goose ──(résultat de l'outil)──► Modèle ──► rédige le rapport ──► Analyste
```

**Les trois points clés :**
- **Le modèle ne touche jamais Wazuh directement.** Il *demande* un outil ; c'est Goose, dans la sandbox, qui l'exécute.
- **Il ne peut demander que nos 4 outils, tous en lecture seule.** Même s'il « voulait » bloquer une IP ou lancer une commande, l'outil n'existe pas.
- **Ce qui part chez NVIDIA :** la question et les résultats des outils (des alertes du labo). Acceptable ici car aucune donnée réelle (règle du projet). En entreprise, ce serait un point à valider, ou une raison d'héberger le modèle en local.

## Le serveur MCP `wazuh_mcp.py`

Écrit en Python **sans aucune dépendance externe** (bibliothèque standard uniquement). Il parle le protocole MCP (JSON-RPC 2.0, un message par ligne sur l'entrée/sortie standard) et n'utilise que l'API **`_search`** de l'indexeur : il ne peut ni écrire ni supprimer.

| Outil | Ce qu'il renvoie |
|---|---|
| `resume_alertes` | Total des alertes sur une période, regroupées par règle, par IP source et par machine |
| `rechercher_alertes` | Les N alertes les plus récentes (max 10), filtrables par machine, IP, groupe de règles |
| `activite_ip` | Profil d'une IP : volume, première et dernière activité, règles déclenchées, utilisateurs tentés, machines ciblées, techniques MITRE ATT&CK |
| `inventaire_actifs` | L'inventaire de l'étape 1 (relie la détection à la connaissance des actifs) |

Chaque outil porte l'annotation MCP `readOnlyHint: true`.

## Démonstration réalisée (13/11/2026)

Question posée :
> Fais un rapport d'investigation sur les alertes SSH des dernières 24 heures.

**Démarche suivie par l'IA**, chaque appel validé par l'analyste :
1. `resume_alertes` → 517 alertes, dont les règles SSH/PAM.
2. `activite_ip(172.30.0.100)` → 107 événements entre 19:50:02 et 19:53:16, cible `srv-ssh`, MITRE *Brute Force / Password Guessing*.
3. `rechercher_alertes(groupe=authentication_success)` → **0 résultat** : vérification qu'aucune connexion n'a réussi.
4. `inventaire_actifs` → identification de `172.30.0.100` comme le poste scanner du labo.

**Résultat :** un rapport complet en 6 parties (résumé, chronologie, source/cible, interprétation, gravité « moyenne » justifiée, recommandations immédiates et de durcissement). Voir [rapport-investigation-ia-2026-11-13.md](rapport-investigation-ia-2026-11-13.md).

**Ce qui est remarquable :**
- L'IA s'est posé seule **la question clé de toute enquête** : *l'attaquant est-il entré ?*
- Elle a croisé alertes et inventaire, et noté que la source est le scanner interne, **sans conclure** qu'il s'agit d'un test autorisé (« doit être validé auprès des responsables du laboratoire »).
- Elle distingue ce que les données prouvent de ce qu'elles ne permettent pas de conclure.
- Toutes les actions proposées sont des **recommandations** soumises à validation humaine.

## Limites observées

La relecture humaine a relevé deux erreurs. C'est la justification concrète de la règle « l'humain valide » :

| Erreur | Détail | Leçon |
|---|---|---|
| **Résultats attribués au mauvais appel** | Deux recherches étaient lancées en parallèle ; l'IA a attribué les 67 résultats de la recherche `sshd` à la recherche `authentication_success` (qui en avait 0). Elle a toutefois remarqué l'incohérence et n'en a pas tiré de fausse conclusion. | Un rapport IA se relit ; les chiffres se vérifient à la source (dashboard Wazuh). |
| **Caractère parasite** | « Comptes尝试 recensés » : un mot chinois inséré au milieu du français. | Les modèles multilingues peuvent dériver ; relecture nécessaire avant diffusion. |

## Problèmes rencontrés (et leçons)

| Problème | Cause | Solution |
|---|---|---|
| `Approval required for integrate.api.nvidia.com` | Politique réseau Balanced : domaine non autorisé | `sbx policy allow network integrate.api.nvidia.com` |
| Modèle Kimi : « API access not available » | Certains modèles du catalogue sont réservés au *playground* | Choisir un modèle au badge **Free Endpoint** |
| Réponse `content: null` au test `curl` | MiniMax est un modèle à raisonnement ; avec `max_tokens: 50` il a tout utilisé pour réfléchir | Normal ; Goose ne fixe pas de limite aussi basse |
| `CERTIFICATE_VERIFY_FAILED … key usage extension` | Python ≥ 3.13 applique `VERIFY_X509_STRICT` ; la CA générée par Wazuh n'a pas l'extension *keyUsage* | On garde la vérification par **notre** CA, on retire seulement le mode strict. En production : régénérer la CA conforme |
| HTTP 401 Unauthorized | `.env` contenait un mot de passe choisi (`12345678`) au lieu de celui de Wazuh | La variable doit **contenir** le mot de passe existant de Wazuh, pas en choisir un |
| Script Goose : `Detected OS: windows` | Le chemin `/c/Projets/...` ressemble à Git Bash sous Windows | Lancer l'installation depuis `~` |
| `bzip2` introuvable | Liste des paquets jamais téléchargée dans la sandbox | `sudo apt-get update` d'abord |
| Rapport très lent (plusieurs minutes) | L'IA demandait `limite: 100` sur 7 recherches → des milliers de lignes de JSON à relire | Plafond à 10 résultats, champs allégés, méthode d'enquête dans `.goosehints` (« résumés d'abord, 4 appels max ») → rapport en ~1 minute |

**Leçon sur la performance :** la qualité d'un agent IA dépend autant de **ce qu'on lui donne à lire** que du modèle. Des outils qui renvoient des **résumés** plutôt que des données brutes rendent l'agent plus rapide, moins cher et plus fiable.

## Installation (rappel)

```powershell
# PowerShell
sbx policy allow network integrate.api.nvidia.com
```
```bash
# Sandbox
sudo apt-get update && sudo apt-get install -y bzip2
cd ~ && curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
cd /c/Projets/cybersentinel-ai
export PATH="$HOME/.local/bin:$PATH"
bash ai-agent/start-goose.sh
```
`.env` : `NVIDIA_API_KEY`, `NVIDIA_MODEL=minimaxai/minimax-m3.1-flash`, `SIEM_ADMIN_PASSWORD=SecretPassword`.

## Questions probables du jury
- *Pourquoi ne pas laisser l'IA bloquer l'attaquant elle-même ?* → Une IA peut se tromper (on l'a constaté). Une action de blocage sur une mauvaise IP peut couper un service légitime. L'IA recommande, l'humain décide.
- *Qu'est-ce que MCP apporte ?* → Un standard : le même serveur `wazuh_mcp.py` fonctionnerait avec d'autres agents compatibles MCP. On ne réécrit pas l'intégration à chaque outil.
- *L'IA invente-t-elle des choses ?* → Elle est consignée à n'utiliser que les données des outils, et dans notre démo elle a signalé ce que les données ne permettaient pas de conclure. Mais l'erreur d'attribution montre que la relecture reste indispensable.
- *Et si la clé API fuit ?* → Elle est seulement dans `.env` (ignoré par Git) et passée en variable d'environnement. En cas de fuite : la révoquer sur build.nvidia.com et en générer une nouvelle.
