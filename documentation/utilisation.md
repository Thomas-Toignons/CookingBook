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

Le nouveau tirage affecte au lundi midi suivant la nouvelle recette du dimanche soir. Le mode `publier` refuse `--semaine` et `--nouveau-tirage` : il exporte toujours le planning courant.

Le workflow utilise aussi le mode `automatique` lors d'un push sur `main` :

```bash
python3 scripts/principal.py automatique
```

Ce mode publie le planning courant sans changer les recettes. Si aucun menu daté n'existe dans la base, il initialise le premier menu pour la semaine courante. Il ne crée pas une nouvelle semaine lors des pushes suivants, même si le planning enregistré est ancien : la génération hebdomadaire reste réservée au traitement du lundi. Les changements de règles prennent effet à la prochaine génération ; un push des règles ne refait pas le tirage courant.

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

Le modèle et les vues SQL sont lus depuis le dépôt du code, indépendamment de l'emplacement de la base. Le workflow utilise désormais directement le code et la base de `main` ; les chemins personnalisés restent utiles pour les essais sur une copie.

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
- **Semaines sautées** : générer directement la semaine souhaitée. Chaque planning inclut son propre lundi midi suivant ; aucun rattrapage des semaines précédentes n’est nécessaire.
- **Semaine antérieure au planning courant** : refus pour protéger la continuité de l'historique.
- **Exports incomplets après un incident disque** : relancer `publier`.

Pour restaurer une sauvegarde, fermer LibreOffice et tout autre accès à la base, conserver une copie de la base actuelle, puis remplacer `cookBook` par la sauvegarde choisie. L'historique est restauré avec la base ; relancer `publier` pour reconstruire les exports.

## Renseigner les conditionnements

Dans LibreOffice, ouvrir « Ingredients » et saisir « Conditionnement (g / ml / pièces) » dans l'unité de référence de l'ingrédient. Laisser vide pour acheter exactement la quantité manquante. Pour des tomates vendues uniquement par lot de 1200 g, saisir 1200 ; pour une boîte achetable seule de 400 g, saisir 400. Pour des œufs vendus par six, saisir 6 avec l'unité piece.

Le stock est retiré avant l'arrondi au nombre de lots. Les prix restent exprimés pour `base_tarifaire` : si un lot de 1200 g coûte 2,40 €, renseigner soit 2,40 avec une base de 1200, soit 2,00 avec une base de 1000. Les deux tarifs, estimé et magasin, utilisent la même base.

## Première migration vers le lundi midi suivant

Fermer LibreOffice puis lancer `python3 scripts/principal.py publier`. Le programme sauvegarde la base, ajoute le champ de conditionnement et convertit le lundi midi courant en lundi midi suivant sans nouveau tirage. Les tailles de paquets restent vides et les présences sont conservées : vérifier la présence du lundi midi, car une ancienne exclusion pour un repas déjà préparé ne représente plus une absence le lundi suivant.
