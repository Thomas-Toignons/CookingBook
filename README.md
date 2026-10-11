# CookingBook

Recettes et planning dans SQLite, génération hebdomadaire en Python, liste de courses consultable sur GitHub Pages.

Le menu contient **sept dîners distincts : cinq végétariens et deux non végétariens**. Le dîner est repris au déjeuner du lendemain. Le tirage ignore les présences ; elles restent renseignées manuellement et sont prises en compte uniquement par la vue des courses.

## Contraintes pour créer de nouvelles recettes

Les recettes sont destinées à un étudiant avec **un petit budget et une petite cuisine**. Le matériel disponible est limité à **deux plaques de cuisson, une casserole et une poêle**. Les recettes doivent pouvoir être réalisées avec ce matériel, sans nécessiter de four, de robot ou d'équipement supplémentaire.

L'objectif est de **préparer en une seule fois deux portions : une pour le dîner et une pour le déjeuner du lendemain, au coût le plus bas possible**. Pour les futures propositions de plats :

- Privilégier les plats complets préparés dans une seule casserole ou une seule poêle, avec le moins de préparations et de vaisselle possible.
- Si plusieurs cuissons sont nécessaires, rester dans la limite des deux plaques et des deux récipients disponibles, en préparant toujours les deux portions ensemble.
- Utiliser des ingrédients économiques, faciles à trouver et communs à plusieurs recettes pour limiter les achats et le gaspillage.
- Éviter les ingrédients coûteux ou spécifiques dont le reste du paquet serait difficile à réutiliser. Tenir compte du coût d'achat des paquets, en plus du coût par portion.
- Prévoir des plats rassasiants qui restent agréables à manger le lendemain et indiquer leur conservation et leur réchauffage dans la fiche recette.
- Renseigner des quantités de référence pour **deux portions** (`portions_reference = 2`) et préciser si le plat se prépare dans un seul récipient (`tout_en_un`). Le planning peut ensuite adapter les quantités aux portions prévues.
- Proposer suffisamment de recettes végétariennes pour respecter le menu hebdomadaire : cinq dîners végétariens et deux non végétariens.

Ces indications guident la création de nouvelles recettes. Le script hebdomadaire sélectionne les recettes déjà présentes dans SQLite ; il ne crée pas de nouveaux plats et n'optimise pas automatiquement leur coût.

## Démarrage local

Python **3.11 ou supérieur**, sans dépendance à installer. Les commandes s'exécutent depuis la racine du dépôt. Fermer les formulaires LibreOffice avant de modifier la base avec le script.

```bash
python3 scripts/principal.py generer
```

Cette commande met à jour `cookBook`, exporte `menus/historique.json` et produit `docs/index.html` et `docs/courses.csv`. Une sauvegarde SQLite est créée dans `backups/` avant le traitement.

Pour actualiser les courses après modification des présences, portions ou stocks, sans modifier le menu :

```bash
python3 scripts/principal.py publier
```

Pour voir un tirage sans modifier la base :

```bash
python3 scripts/generer_menu.py
```

## Documentation

- [Fonctionnement et organisation](documentation/fonctionnement.md)
- [Règles et commandes](documentation/utilisation.md)
- [Git, modifications manuelles et GitHub Pages](documentation/github-pages.md)

## Organisation des branches

`main` contient le code, les règles et le modèle HTML. `menus` conserve la base utilisée au quotidien, l'historique et le site généré. Le workflow crée `menus` depuis `main` si elle n'existe pas, puis utilise toujours sa dernière base. La base de `main` sert seulement à l'initialisation et aux tests.

Ne pas fusionner une ancienne base de `main` par-dessus celle de `menus`. Le workflow exécute le code de `main` sans remplacer les données de `menus`.

## Vérifications

```bash
python3 -m unittest discover -s tests -v
```

Les tests utilisent des copies temporaires de la base et ne modifient pas `cookBook`.
