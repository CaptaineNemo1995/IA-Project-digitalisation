# CyberSentinel AI

> PoC Blue Team / SOC : découverte d'actifs, centralisation SIEM/XDR, détection et investigation assistée par IA, dans un laboratoire isolé et portable.

![Statut](https://img.shields.io/badge/statut-en%20construction-orange)
![Type](https://img.shields.io/badge/type-Proof%20of%20Concept-blue)
![RAM](https://img.shields.io/badge/RAM%20max-12%20Go-green)

---

## Objectif

Démontrer une chaîne de défense complète dans un environnement contrôlé :

```
Découverte des actifs → Inventaire → SIEM/XDR → Surveillance → Détection → Investigation IA → Rapport
```

Principe de base : **on ne peut pas protéger ce qu'on ne connaît pas.**

## Principes du dépôt

| Principe | Application |
|---|---|
| **Portabilité** | Tout le labo est décrit en code dans ce dépôt. `git clone` + une commande = labo reconstruit. |
| **Isolation** | Le labo tourne dans une sandbox Docker Sandboxes (microVM), sur un réseau interne sans exposition Internet. |
| **Ressources limitées** | Budget total **12 Go de RAM maximum** pour tourner sur des machines à 16 Go. Chaque conteneur a un `mem_limit`. |
| **Aucun secret dans Git** | Clés API et mots de passe dans `.env` (ignoré). Seul `.env.example` est versionné. |

## Architecture

| Composant | Rôle | Statut |
|---|---|---|
| Docker Sandboxes (`sbx`) | Isolation microVM du labo | ⏳ À installer |
| Docker Compose | Déploiement des services du labo | ⏳ |
| Machines cibles | Hôtes Linux + SSH servant de cibles | ⏳ |
| Python | Découverte, collecte, structuration des données | ⏳ |
| SIEM/XDR (Wazuh pressenti) | Centralisation et détection | ⏳ |
| Goose + MCP | Agent IA et accès contrôlé aux données | ✅ Goose installé |
| NVIDIA NIM API | Modèle IA pour l'analyse | ⏳ Clé à créer |

## Budget RAM (12 Go max)

| Service | Limite |
|---|---|
| SIEM (Wazuh single-node, heap réduit) | ~5 Go |
| Machines cibles (×3) | 256 Mo chacune |
| Scripts Python | 512 Mo |
| Goose + MCP | 512 Mo |
| Surcoût microVM | ~1 Go |
| Marge | ~4 Go |

## Prérequis

- Windows 11 avec **Windows Hypervisor Platform** activé
- Docker Sandboxes : `winget install Docker.sbx`
- Git
- 16 Go de RAM minimum sur la machine hôte

## Démarrage rapide

```bash
git clone <URL_DU_DEPOT> cybersentinel-ai
cd cybersentinel-ai
cp .env.example .env        # puis remplir les valeurs
# Les commandes de lancement du labo seront ajoutées à l'étape 1
```

## Structure du dépôt

```
cybersentinel-ai/
├── lab/            # docker-compose et définition du labo isolé
│   ├── targets/    # images des machines cibles
│   └── siem/       # configuration SIEM/XDR
├── discovery/      # étape 1 : scripts de découverte et d'inventaire
├── detection/      # étape 3 : règles et scénarios (SSH brute force…)
├── ai-agent/       # étape 4 : config Goose, serveurs MCP
├── scripts/        # utilitaires (setup, sauvegarde, reset)
├── docs/           # documentation, rapports, captures
│   └── inventaire/ # livrables de l'étape 1
├── .env.example
└── CONTRIBUTING.md
```

## Feuille de route

- [ ] **Étape 0** : dépôt Git, installation de Docker Sandboxes, réseau isolé
- [ ] **Étape 1** : découverte des actifs → inventaire + cartographie
- [ ] **Étape 2** : intégration SIEM/XDR
- [ ] **Étape 3** : scénario de détection SSH brute force
- [ ] **Étape 4** : investigation assistée par IA (Goose + MCP + NVIDIA NIM)
- [ ] **Étape 5** : validation de bout en bout et documentation finale

Chaque étape est validée avant de passer à la suivante.

## Règles de sécurité

- Scans et tests **uniquement** sur les machines du labo
- Aucune exposition inutile à Internet ; réseau interne isolé
- Aucune donnée réelle ou sensible
- L'agent IA n'exécute **aucune** commande arbitraire ; validation humaine pour toute action sensible
- Journaux conservés ; le labo peut être détruit et recréé à tout moment

## Équipe

| Membre | Rôle |
|---|---|
| … | … |

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

---

*Projet académique : Master 2 Cybersécurité, novembre 2026.*
