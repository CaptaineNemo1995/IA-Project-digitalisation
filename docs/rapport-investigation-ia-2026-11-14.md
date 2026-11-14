> **Document généré par l'agent IA** (Goose + MiniMax M3.1 Flash via NVIDIA NIM, outils MCP Wazuh en lecture seule), le 14/11/2026, en 4 min 16 s.
> Reproduit **sans modification**. La relecture humaine y relève 3 mots parasites en langue étrangère (« 图识 », « esperada », « seriousness ) — voir [etape4-ia.md](etape4-ia.md).

# Rapport d’investigation — Alertes SSH de la dernière heure

**Période analysée :** 14 novembre 2026, 19:01–20:01 UTC
**Périmètre :** alertes Wazuh liées à SSH, PAM et à la vérification des mots de passe
**Actions de remédiation :** aucune ; les mesures ci-dessous sont des recommandations à valider.

## 1. Résumé

Wazuh a enregistré **122 alertes**, dont **120 liées à l’authentification SSH** et 2 au démarrage de composants Wazuh. **107 événements sont attribués à une source unique**, `172.30.0.100`, et se concentrent en environ trois minutes contre `srv-ssh`.

L’activité correspond à une **attaque par force brute et devinette de mots de passe**, avec plusieurs comptes visés. Les traces disponibles indiquent des échecs d’authentification : **aucune alerte `authentication_success` n’a été trouvée** pendant la période.

## 2. Chronologie et volume

| Indicateur                                | Observation                                                                                                                  |
|-------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| Première activité de la source            | **19:39:02 UTC**                                                                                                             |
| Dernière activité de la source            | **19:42:12 UTC**                                                                                                             |
| Concentration                             | Environ **3 minutes 10 secondes**                                                                                            |
| Événements rattachés à `172.30.0.100`     | **107**                                                                                                                      |
| Alertes d’authentification SSH/PAM/chkpwd | **120**                                                                                                                      |
| Machines concernées                       | `srv-ssh` : **121 alertes**, incluant le démarrage de l’agent ; `wazuh.manager` : **1 alerte**, liée au démarrage du serveur |
### Répartition des 120 alertes d’authentification

- 51 : tentative de connexion avec un utilisateur inexistant ;
- 35 : échec d’authentification PAM ;
- 13 : échec de vérification du mot de passe ;
- 12 : échec d’authentification SSH ;
- 5 : échecs multiples d’authentification sur une courte période ;
- 3 : détection de force brute avec utilisateur inexistant ;
- 1 : détection de force brute avec échec d’authentification.

Exemples observés autour de 19:42 :

- `19:42:07` — utilisateur inexistant `test` ;
- `19:42:09` — nouvel essai avec `test` ;
- `19:42:10` — mot de passe incorrect pour `oracle` ;
- `19:42:10` — mot de passe incorrect pour `labuser`.

## 3. Source et cible

- **Source principale et unique recensée :** `172.30.0.100`
- **Cible :** `srv-ssh`
- **Comptes，图识 tentés :** `oracle`, `test`, `user`, `admin`
- **Autre compte visible dans un exemple d’alerte :** `labuser`
- **Autres machines ciblées :** aucune recensée par le profil d’activité.

La présence d’utilisateurs inexistants et de comptes « plausibles » suggère une **énumération de comptes suivie de tentatives de mots de passe**.

## 4. Interprétation

### Nature de l’activité

Les règles Wazuh classent cette activité en :

- **Brute Force** ;
- **Password Guessing** ;
- **SSH**.

Le profil présente les caractéristiques d’une **attaque par force brute SSH** : forte concentration temporelle, répétition de tentatives, rotation de plusieurs noms d’utilisateur et déclenchement de règles de niveau 10.

### Succès ou échec

Les alertes observées sont exclusivement des échecs. La recherche du groupe `authentication_success` sur la dernière heure retourne **0 résultat**.

Cela indique qu’**aucune connexion réussie n’est visible dans les données Wazuh examinées**. Cela ne suffit toutefois pas à exclure une compromission par un autre vecteur ou une tentative de connexion qui n’aurait pas été journalisée.

## 5. Gravité

**Gravité : élevée**

Justification :

- 107 événements d’authentification attribués à une seule source en un intervalle très court ;
- plusieurs comptes systématiquement visés ;
- activation de règles Wazuh de niveau 10 ;
- ciblage direct d’un service SSH d’administration ;
- aucune authentification réussie recensée, ce qui réduit le niveau de compromission avérée mais pas la seriousness de la tentative.

La source `172.30.0.100` doit notamment être rapprochée des scanners autorisés et des fenêtres de test. Si elle est légitime, une partie des alertes pourrait être une activité de validation esperada.

## 6. Recommandations

### Immédiates — après validation humaine

1. **Vérifier le caractère légitime de `172.30.0.100`** : scan d’inventaire, test de sécurité planifié ou activité non reconnue.
2. Si elle n’est pas autorisée, **recommandation de blocage temporaire** de cette adresse au niveau des contrôles d’accès SSH, avec validation préalable par l’équipe responsable.
3. **Restreindre temporairement l’accès SSH** aux adresses et réseaux de gestion autorisés.
4. Examiner les journaux d’authentification natifs de `srv-ssh` pour les comptes `oracle`, `test`, `user`, `admin` et `labuser`, à la recherche de connexions réussies non remontées par Wazuh.
5. Vérifier les indicateurs de compromission sur `srv-ssh` : clés `authorized_keys`, sessions et processus inhabituels, tâches planifiées, services ou modifications récentes.

### Durcissement

- Désactiver l’authentification SSH par mot de passe au profit de clés SSH ;
- Interdire les connexions root directes ;
- Restreindre les comptes autorisés avec `AllowUsers` ou une liste équivalente ;
- Réduire `MaxAuthTries` et configurer un mécanisme de limitation/rate limiting ;
- Segmenter l’administration SSH et appliquer des règles de pare-feu par source ;
- En cas d’activité malveillante confirmée, réinitialiser les identifiants concernés et revoquer les clés ou jetons associés ;
- Si l’adresse est un scanner autorisé, documenter l’activité et ajuster la détection afin de distinguer les tests planifiés des forces brutes réelles.
