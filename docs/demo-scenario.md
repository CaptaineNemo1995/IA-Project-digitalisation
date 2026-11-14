# Scénario de démonstration — CyberSentinel AI

**Durée : ~12 minutes.** Deux terminaux dans la sandbox + le navigateur sur le dashboard Wazuh.

Fil rouge à dire au jury :
> « On ne peut pas protéger ce qu'on ne connaît pas. On va découvrir le réseau, l'attaquer, voir le SOC détecter l'attaque, puis laisser une IA mener l'enquête — sous contrôle humain. »

---

## Avant le jury (15 min avant, une seule fois)

**PowerShell :**
```powershell
cd C:\Projets\cybersentinel-ai
sbx run --name cybersentinel
```

**Terminal 1 (sandbox) :**
```bash
docker compose up -d
bash scripts/setup-siem.sh
export PATH="$HOME/.local/bin:$PATH"
```

**PowerShell (une autre fenêtre) :**
```powershell
sbx ports cybersentinel --publish 8443:443
```

**Terminal 2 (sandbox) :** ouvrir une deuxième session dans la même sandbox
```powershell
sbx exec -it cybersentinel bash
```
```bash
cd /c/Projets/cybersentinel-ai
```

**Navigateur :** `https://localhost:8443`, connexion `admin` / `SecretPassword`, laisser ouvert sur **Threat Hunting**.

**Vérifications rapides :**
- [ ] `docker compose ps` : 4 conteneurs `Up`
- [ ] `docker exec single-node-wazuh.manager-1 /var/ossec/bin/agent_control -l` : `srv-ssh` **Active**
- [ ] Dashboard Wazuh qui s'affiche
- [ ] `docs/rapport-investigation-ia-2026-11-13.md` ouvert dans VS Code (plan B)

---

## Acte 1 — Le contexte (1 min)

**Montrer :** le README sur GitHub (schéma d'architecture).

**Dire :**
- Un laboratoire **isolé** : une microVM Docker Sandboxes, un réseau sans Internet.
- **Portable** : tout est décrit en code dans Git ; n'importe quel membre reconstruit le labo.
- **Économe** : moins de 2 Go de RAM réellement utilisés, plafond à 10 Go.

---

## Acte 2 — Isolation et découverte (2 min 30)

**Terminal 1 :**
```bash
docker compose exec scanner ping -c 2 8.8.8.8
```
**Dire :** « Network is unreachable : le labo ne peut rien envoyer vers l'extérieur. »

**Terminal 2 — lancer l'attaque MAINTENANT** (elle dure ~3 min, elle tourne pendant qu'on présente la découverte) :
```bash
docker compose exec scanner nmap -p 22 --script ssh-brute \
  --script-args userdb=/work/users.txt,passdb=/work/pass.txt,brute.firstonly=true \
  172.30.0.10
```
**Dire :** « Pendant qu'on parle, un attaquant essaie de deviner les mots de passe SSH. On y revient dans deux minutes. »

**Terminal 1 :**
```bash
docker compose exec scanner python3 discover.py
cat discovery/output/inventaire.md
```
**Dire :**
- 5 actifs, dont la **passerelle Docker** qu'on n'avait pas déclarée.
- **L'angle mort** : un scan nmap par défaut ne voit pas Redis (port 6379 hors des 1000 ports courants). Il a fallu un scan complet (`-p-`).
- Redis est exposé **sans mot de passe** : une mauvaise configuration volontaire, repérée par l'inventaire.

---

## Acte 3 — La détection (2 min)

**Terminal 2 :** attendre la fin de nmap → `No valid accounts found`.
**Dire :** « L'attaque a échoué : le mot de passe n'était pas dans le dictionnaire. Mais le SOC l'a-t-il vue ? »

**Navigateur — Threat Hunting**, barre de recherche :
```
agent.name:srv-ssh and rule.level>=10
```
**Montrer :** les alertes **« sshd: brute force trying to get access to the system »** et **« PAM: Multiple failed logins »**, avec la technique **MITRE ATT&CK : Brute Force / Password Guessing**.

**Dire :**
- Un échec isolé = un **événement**. Beaucoup d'échecs, même source, peu de temps = une **corrélation** → alerte de niveau 10.
- La chaîne : sshd → rsyslog → agent Wazuh → manager → indexeur → dashboard.

---

## Acte 4 — L'enquête par l'IA (4 min)

**Terminal 1 :**
```bash
bash ai-agent/start-goose.sh
```
Question à taper :
```
Fais un rapport d'investigation sur les alertes SSH de la dernière heure.
```

**À chaque demande d'approbation, s'arrêter et dire :**
> « L'IA demande la permission avant chaque action. Elle n'a que 4 outils, tous en lecture seule. Elle ne peut ni exécuter de commande, ni bloquer une IP. »

Choisir **Allow** (jamais *Always Allow* pendant la démo).

**Pendant qu'elle rédige, expliquer le fonctionnement :**
- Le modèle (MiniMax, chez NVIDIA) **ne touche jamais Wazuh** : il *demande* un outil, Goose l'exécute dans la sandbox.
- La clé API ne quitte jamais le `.env` (ignoré par Git).

**Sur le rapport, pointer :**
- Elle vérifie seule la question clé : **l'attaquant est-il entré ?** → aucune connexion réussie.
- Elle croise avec l'inventaire : `172.30.0.100` = notre scanner, mais elle **ne conclut pas** que c'est autorisé.
- Ses actions sont des **recommandations** à valider.

**Dire, pour finir l'acte :**
> « Hier, en relisant un rapport, on a trouvé deux erreurs de l'IA : des résultats attribués au mauvais appel, et un mot en chinois au milieu du texte. C'est exactement pour ça que l'humain valide. »

---

## Acte 5 — Conclusion (1 min)

**Dire :**
- La chaîne complète : **Découverte → Inventaire → SIEM → Détection → Investigation IA → Rapport**.
- Les principes respectés : isolation, portabilité, moindre privilège, validation humaine.
- Pistes d'amélioration : réponse active (blocage d'IP) avec validation humaine, mots de passe Wazuh par défaut à changer, modèle IA hébergé en local pour ne rien envoyer à l'extérieur.

---

## Plans B

| Si… | Alors… |
|---|---|
| L'IA est lente (> 2 min) | Pendant l'attente, ouvrir `docs/rapport-investigation-ia-2026-11-13.md` : « voici le rapport produit hier sur la même attaque » |
| NVIDIA ne répond pas | Montrer ce même rapport, et la capture de la demande d'approbation |
| Le dashboard Wazuh ne charge pas | Terminal : `docker exec single-node-wazuh.manager-1 sh -c "grep -oE '\"description\":\"[^\"]*\"' /var/ossec/logs/alerts/alerts.json \| sort \| uniq -c \| sort -rn \| head"` |
| nmap est encore en cours à l'acte 3 | Montrer d'abord les alertes déjà là (Wazuh détecte pendant l'attaque) |
| L'agent `srv-ssh` n'est pas Active | `docker compose restart target-ssh`, attendre 30 s |

## Timing

| Acte | Durée | Cumul |
|---|---|---|
| 1. Contexte | 1:00 | 1:00 |
| 2. Isolation + découverte (attaque lancée) | 2:30 | 3:30 |
| 3. Détection | 2:00 | 5:30 |
| 4. Enquête IA | 4:00 | 9:30 |
| 5. Conclusion | 1:00 | 10:30 |
| Marge | 1:30 | 12:00 |
