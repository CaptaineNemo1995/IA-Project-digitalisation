# Étape 0 : Environnement isolé et portable

## Objectif
Avant de toucher au moindre outil de sécurité, préparer un environnement :
1. **portable** : reconstructible sur n'importe quel PC de l'équipe ;
2. **isolé** : rien de ce qu'on fait (scans, attaques simulées, agent IA) ne doit atteindre le vrai réseau ;
3. **économe** : il doit tourner sur des machines à 16 Go de RAM.

## Ce qui a été fait

| Action | Outil | Résultat |
|---|---|---|
| Création du dépôt Git | Git + GitHub | Tout le projet est décrit en fichiers (Infrastructure as Code) |
| Gestion des secrets | `.env` / `.env.example` / `.gitignore` | Les mots de passe et clés API ne partent jamais sur GitHub |
| Fins de ligne | `.gitattributes` | Les scripts écrits sous Windows fonctionnent dans Linux |
| Création de la sandbox | Docker Sandboxes (`sbx`) | microVM `cybersentinel` : 10 Go RAM, 2 CPU, Debian 13 |
| Politique réseau | `sbx policy` (Balanced) | Sorties Internet bloquées sauf sites autorisés |

Commande de création :
```powershell
sbx run shell --name cybersentinel --memory 10g --cpus 2 .
```

## Les notions à comprendre

**Git / dépôt.** Un historique de toutes les versions des fichiers du projet. Chaque membre « clone » le dépôt, travaille sur une **branche**, puis propose ses changements via une **Pull Request** relue par un autre membre.

**Infrastructure as Code.** Au lieu d'installer le labo « à la main », on l'écrit dans des fichiers (`docker-compose.yml`, `Dockerfile`). Avantage : le labo est reproductible à l'identique, versionné, et documenté par son propre code.

**Le fichier `.env`.** Contient les valeurs secrètes (mots de passe, clé API). Il est listé dans `.gitignore`, donc Git l'ignore. On versionne seulement `.env.example`, un modèle sans vraies valeurs.

**Conteneur vs machine virtuelle vs microVM.**
- Un **conteneur** (Docker) isole un programme, mais **partage le noyau** du système hôte. Léger, mais une faille du noyau peut permettre de s'échapper.
- Une **machine virtuelle** a **son propre noyau** : isolation forte, mais lourde.
- Une **microVM** (Docker Sandboxes) est une VM réduite au strict nécessaire : noyau propre (isolation forte) et démarrage en quelques secondes (légèreté).

**Pourquoi Docker Sandboxes ?** La sandbox a son **propre daemon Docker privé** : on peut y lancer tout le labo (`docker compose`) sans donner de privilèges sur la machine hôte. Si quelque chose tourne mal (y compris l'agent IA), on supprime la sandbox et on la recrée depuis Git.

**La politique réseau Balanced.** Tout est bloqué par défaut, sauf une liste de sites de développement. Exemple vécu : le téléchargement des paquets Debian a échoué jusqu'à ce qu'on autorise explicitement `deb.debian.org` :
```powershell
sbx policy allow network deb.debian.org
```
C'est le principe du **moindre privilège** appliqué au réseau.

## Alternatives écartées

| Option | Pourquoi pas |
|---|---|
| Docker Compose seul | Isolation plus faible (noyau partagé avec l'hôte) |
| Vagrant + VirtualBox | Lourd en RAM, conflits avec WSL2/Hyper-V |
| Politique réseau « Open » | Aucun contrôle des sorties : contraire à l'objectif |
| Politique « Locked Down » | Trop stricte pour la phase d'installation |

## Validation

| Test | Commande | Résultat |
|---|---|---|
| RAM | `free -h` | 9,8 Gi |
| CPU | `nproc` | 2 |
| Docker privé | `docker version` | Client + serveur 29.9.3 |
| Dépôt monté | `ls -la` | Fichiers visibles dans `/c/Projets/cybersentinel-ai` |

## Questions probables du jury
- *Pourquoi ne pas tout installer directement sur Windows ?* → Les scans toucheraient le vrai réseau, et un agent IA aurait accès à la machine.
- *Comment un autre membre reproduit le labo ?* → `git clone`, copie du `.env`, création de la sandbox, `docker compose up`.
- *Que se passe-t-il si la sandbox est compromise ?* → Elle est jetable : `sbx rm`, puis recréation depuis Git. L'hôte n'est pas touché (frontière matérielle de la microVM).
