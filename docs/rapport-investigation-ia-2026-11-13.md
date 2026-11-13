> **Document généré par l'agent IA** (Goose + MiniMax M3.1 Flash via NVIDIA NIM, outils MCP Wazuh en lecture seule), le 13/11/2026.
> Reproduit **sans modification**, comme preuve de l'étape 4. Les erreurs de l'IA relevées à la relecture humaine sont listées dans [etape4-ia.md](etape4-ia.md#limites-observées).

# Rapport d’investigation — Alertes SSH des dernières 24 heures

**Période analysée :** fenêtre glissante de 24 heures se terminant le **13/11/2026 à 21:41 UTC**.
**Périmètre :** alertes Wazuh, niveau minimum 0.

## 1. Résumé

Wazuh recense **517 alertes** sur la période. Les règles explicitement liées à l’authentification SSH et à PAM représentent **116 alertes**, principalement sur `srv-ssh`. L’activité SSH est concentrée sur une seule source, **172.30.0.100** (`soc-scanner`), et correspond à une rafale de tentatives par mots de passe contre plusieurs comptes.

Les exemples observés sont exclusivement des échecs. **Aucune connexion réussie n’est attestée par les données disponibles.** L’IP source correspond au poste scanner du laboratoire, ce qui peut indiquer une activité de test, mais les alertes ne permettent pas d’en confirmer l’autorisation.

## 2. Chronologie et volume

| Indicateur                            | Observation                       |
|---------------------------------------|-----------------------------------|
| Total des alertes Wazuh               | **517**                           |
| Alertes sur `srv-ssh`                 | **330**                           |
| Alertes sur `wazuh.manager`           | **187**                           |
| Règles SSH/PAM listées                | **116 alertes**                   |
| Événements attribués à `172.30.0.100` | **107**                           |
| Première activité de la source        | **13/11/2026 19:50:02 UTC**       |
| Dernière activité de la source        | **13/11/2026 19:53:16 UTC**       |
| Durée de la rafale observée           | **environ 3 minutes 14 secondes** |
### Principales règles

| Règle                                                                      | Nombre | Niveau maximal |
|----------------------------------------------------------------------------|--------|----------------|
| `sshd: Attempt to login using a non-existent user`                         |     51 |              5 |
| `PAM: User login failed.`                                                  |     35 |              5 |
| `unix_chkpwd: Password check failed.`                                      |     13 |              5 |
| `sshd: authentication failed.`                                             |     12 |              5 |
| `PAM: Multiple failed logins in a small period of time.`                   |      3 |         **10** |
| `sshd: brute force trying to get access to the system. Non existent user.` |      2 |         **10** |
> Les volumes par règles et par IP proviennent de regroupements différents : ils ne doivent pas être additionnés directement.

### Exemples d’événements

- `19:53:15.683` — échec pour l’utilisateur inexistant `oracle` depuis `172.30.0.100`.
- `19:53:11.998` — échec pour l’utilisateur inexistant `test`.
- `19:53:12.546` — échec pour l’utilisateur inexistant `user`.
- `19:53:16.530` — échec du mot de passe pour `labuser`.

La recherche avec le groupe `authentication_success` a renvoyé 67 résultats, mais les éléments présentés sont malgré tout des échecs et portent `groupes: null`. Cette sortie ne permet donc **pas de confirmer une authentification réussie**.

## 3. Source et cible

### Source

- **IP :** `172.30.0.100`
- **Nom :** `soc-scanner`
- **Rôle d’inventaire :** poste d’analyse SOC / scanner
- **Cible unique observée :** `srv-ssh`
- **Comptes尝试 recensés par le profil d’activité :** `oracle`, `test`, `user`, `admin`
- **Compte supplémentaire visible dans un exemple de log :** `labuser`

### Cible

- **Agent Wazuh :** `srv-ssh`
- **IP d’inventaire :** `172.30.0.10`
- **Rôle :** cible du laboratoire
- **Service exposé :** SSH/OpenSSH sur le port TCP 22
- **Version observée :** `OpenSSH 10.0p2 Debian 7+deb13u4`

Aucune autre machine cible n’apparaît dans le profil de l’activité SSH.

## 4. Interprétation

Les données sont caractéristiques d’une **tentative automatisée de devinette de mots de passe** contre SSH :

- tentative répétée sur plusieurs identifiants ;
- utilisation de comptes inexistants ;
- échecs PAM et `unix_chkpwd` ;
- détection explicite de **Brute Force** par Wazuh ;
- concentration de 107 événements en environ trois minutes.

**Techniques indiquées par Wazuh :**

- **Brute Force**
- **Password Guessing**
- **SSH**

Les identifiants numériques ATT&CK ne sont pas fournis par les résultats.

### Succès ou échec

Tous les événements montrés sont des échecs d’authentification. Aucun élément disponible ne confirme :

- une session SSH réussie ;
- l’usage d’une clé ou d’un jeton valide ;
- une connexion avec élévation de privilèges ;
- une activité post-authentification.

La source étant le scanner interne du laboratoire, cette rafale peut correspondre à un **test de sécurité autorisé ou à une simulation**. Cette qualification n’est toutefois pas présente dans les données Wazuh et doit être validée auprès des responsables du laboratoire.

## 5. Gravité

### **Moyenne**

**Éléments aggravants :**

- rafale intense de 107 événements sur une courte durée ;
- règles de niveau 10 signalant explicitement le brute force ;
- plusieurs comptes visés ;
- surface SSH directement exposée.

**Éléments limitants :**

- source interne correspondant au poste scanner du laboratoire ;
- cible unique : `srv-ssh` ;
- authentifications observées en échec ;
- aucune intrusion post-authentification confirmée.

La gravité devrait être **reclassée en élevée** si l’activité de `172.30.0.100` n’est pas rattachée à une campagne de test autorisée, ou si une session réussie est retrouvée dans les journaux complets.

## 6. Recommandations

### Immédiates

1. **Faire valider `172.30.0.100`/`soc-scanner`** par le responsable du laboratoire et rapprocher la fenêtre `19:50–19:54 UTC` d’un ticket de test ou d’une campagne de scan.
2. Si l’activité n’est pas autorisée, **isoler ou bloquer temporairement cette source** au niveau des règles réseau, après validation humaine.
3. Examiner les journaux complets `sshd`, PAM et les événements `Accepted`, `session opened`, `publickey` et `password` sur `srv-ssh` pour cette période, afin de confirmer ou d’exclure une session réussie.
4. Vérifier les connexions associées aux comptes `admin`, `labuser`, `oracle`, `test` et `user`, ainsi que les éventuelles clés autorisées et modifications de `authorized_keys`.
5. Prévoir une **rotation des mots de passe** des comptes locaux SSH si le scanner n’était pas censé employer leurs identifiants.

### Durcissement

1. Restreindre l’accès SSH à une **liste d’adresses autorisées** et limiter l’exposition du port 22 au réseau de gestion.
2. Désactiver l’authentification par mot de passe au profit des clés SSH, et activer l’authentification multifacteur lorsque l’infrastructure le permet.
3. Configurer des limitations de tentatives, notamment via `MaxAuthTries`, `LoginGraceTime` et un mécanisme de blocage temporaire comme Fail2Ban.
4. Introduire un compte d’administration nominatif et limiter les comptes susceptibles d’être devinés.
5. Vérifier la politique de correctifs de la version OpenSSH installée ; les données ne permettent pas de conclure à sa vulnérabilité.
6. Si l’activité du scanner est légitime, prévoir une **autorisation formelle et une règle Wazuh adaptée**, tout en conservant les événements dans les journaux à des fins de traçabilité.

**Conclusion :** les données montrent une rafale de brute force SSH échoué contre `srv-ssh`, initiée par `172.30.0.100`. La priorité est de confirmer le caractère autorisé ou non de cette activité ; en l’absence de validation, le risque pour ce serveur SSH doit être considéré comme élevé.