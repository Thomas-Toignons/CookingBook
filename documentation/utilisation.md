# Règles et utilisation locale

## Prérequis

Python 3.11+ avec les modules standard `sqlite3`, `tomllib` et les données de fuseaux horaires système. Les workflows utilisent Python 3.12 sur Ubuntu. Aucune clé API ni bibliothèque Python supplémentaire n'est nécessaire.

## Modifier les règles

Modifier `regles.toml` sur `main` puis pousser la modification.

| Paramètre | Valeur initiale | Comportement |
| --- | --- | --- |
| `menu.nombre_non_vegetariens` | `2` | Nombre exact de dîners non végétariens parmi sept ; entier entre 0 et 7. |
| `menu.recettes_distinctes` | `true` | Tirage sans répétition ; `false` autorise les répétitions. |
| `menu.dejeuner_identique_au_diner_precedent` | `true` | Déjeuners affectés depuis les dîners ; `false` conserve les déjeuners existants. |
| `selection.recettes_actives_uniquement` | `true` | `false` permet aussi de sélectionner les recettes désactivées. |

Les sections et champs inconnus sont refusés pour détecter les fautes de frappe. Les booléens TOML s'écrivent `true` et `false`. Le nombre de jours est fixé à sept dans le script ; aucun paramètre de jours n'est nécessaire.

Un menu existant n'est pas silencieusement modifié après un changement de règles. Pour appliquer ces nouvelles règles à la semaine déjà générée, utiliser explicitement `--nouveau-tirage`. Le mode `publier` permet d'actualiser les courses sans appliquer de nouvelles règles au menu courant.

## Commandes principales

```bash
# Générer la semaine courante ou réutiliser son menu enregistré.
python3 scripts/principal.py generer

# Actualiser les courses, le HTML et l'export historique sans changer les repas.
python3 scripts/principal.py publier

# Remplacer volontairement le tirage de la semaine courante.
python3 scripts/principal.py generer --nouveau-tirage

# Générer une semaine précise. Toute date est ramenée au lundi correspondant.
python3 scripts/principal.py generer --semaine 2026-10-12
```

Le nouveau tirage conserve la recette du lundi midi provenant de la semaine précédente. Le mode `publier` refuse `--semaine` et `--nouveau-tirage` : il exporte toujours le planning courant.

Une relance normale réaffecte les recettes du menu enregistré aux créneaux. Pour conserver une modification manuelle des recettes du planning, utiliser `publier` ; les modifications manuelles de recettes ne réécrivent pas l'historique des dîners. Pour un menu hebdomadaire cohérent dans le temps, laisser le générateur gérer les recettes.

## Chemins personnalisés et essai sur une copie

```bash
mkdir -p /tmp/cookingbook-essai
cp cookBook /tmp/cookingbook-essai/cookBook
python3 scripts/principal.py generer \
  --base /tmp/cookingbook-essai/cookBook \
  --regles regles.toml \
  --sortie /tmp/cookingbook-essai/site \
  --historique /tmp/cookingbook-essai/historique.json
```

Fermer la base avant d'utiliser une copie de fichier avec `cp`. Le programme utilise une sauvegarde SQLite cohérente pour ses propres backups.

Le modèle et les vues SQL sont lus depuis le dépôt du code, indépendamment de l'emplacement de la base. C'est ce qui permet au workflow d'utiliser le code de `main` avec la base de `menus`.

Pour consulter la page générée localement :

```bash
python3 -m http.server 8000 --directory docs
```

Ouvrir `http://localhost:8000`. Arrêter le serveur avec `Ctrl+C`.

## Commandes spécialisées

```bash
# Prévisualisation JSON d'un tirage : aucune écriture dans la base.
python3 scripts/generer_menu.py --base cookBook

# CSV seul à partir de la vue, sans changer le menu.
python3 scripts/exporter_courses.py --base cookBook --sortie courses.csv
```

`appliquer_menu.py` et `generer_site.py` fournissent les fonctions utilisées par l'orchestrateur ; les modes du script principal sont l'interface conseillée pour la mise à jour complète.

## Erreurs et rattrapage

- **Recettes insuffisantes** : ajouter ou réactiver des recettes de la catégorie concernée, ou ajuster les règles.
- **Créneau manquant** : compléter les quatorze créneaux déjeuner/dîner dans `planning_repas` avant de relancer.
- **Règles modifiées / recette désactivée après tirage** : demander un nouveau tirage pour cette semaine.
- **Semaine précédente manquante** : générer les semaines manquantes dans l'ordre avec `--semaine`, puis générer la semaine actuelle. Ce rattrapage représente un menu théorique pour les semaines sautées ; il ne reconstitue pas les repas réellement pris. Les générations intermédiaires écrasent le planning courant mais ne changent pas les présences.
- **Semaine antérieure au planning courant** : refus pour protéger la continuité de l'historique.
- **Exports incomplets après un incident disque** : relancer `publier`.

Pour restaurer une sauvegarde, fermer LibreOffice et tout autre accès à la base, conserver une copie de la base actuelle, puis remplacer `cookBook` par la sauvegarde choisie. L'historique est restauré avec la base ; relancer `publier` pour reconstruire les exports.
