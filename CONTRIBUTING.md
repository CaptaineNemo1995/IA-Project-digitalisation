# Contribuer à CyberSentinel AI

## 1. Première installation

```bash
git clone <URL_DU_DEPOT> cybersentinel-ai
cd cybersentinel-ai
cp .env.example .env
```

Remplissez `.env` avec vos propres valeurs. **Ne le commitez jamais.**

## 2. Branches

- `main` : version stable, qui fonctionne. Personne ne pousse directement dessus.
- Une branche par tâche :

| Préfixe | Usage | Exemple |
|---|---|---|
| `feat/` | nouvelle fonctionnalité | `feat/scan-nmap` |
| `fix/` | correction | `fix/wazuh-memoire` |
| `docs/` | documentation | `docs/inventaire-etape1` |

```bash
git checkout main && git pull
git checkout -b feat/ma-tache
```

## 3. Commits

Format : `type: description courte`

```
feat: ajout du script de découverte réseau
fix: limite mémoire du conteneur wazuh
docs: cartographie de l'étape 1
```

## 4. Pull Request

1. `git push -u origin feat/ma-tache`
2. Ouvrir une Pull Request vers `main`
3. Un autre membre relit et valide avant le merge

## 5. Règles obligatoires

- ❌ Aucun secret (clé API, mot de passe, token) dans le code ou les commits
- ❌ Aucun scan en dehors du réseau du labo
- ✅ Chaque nouveau conteneur a un `mem_limit` (budget total 12 Go)
- ✅ Tout ce qui change le labo est documenté dans `docs/`
- ✅ Tester localement avant d'ouvrir une PR

## 6. Un secret a été commité par erreur ?

Prévenez l'équipe **immédiatement** et **révoquez la clé** (par exemple, régénérer la clé NVIDIA). La supprimer dans un nouveau commit ne suffit pas : elle reste dans l'historique.
