# Fonctionnement du dépôt

## Données existantes

`cookBook` est la base SQLite, sans extension. `cookingBook.odb` est l'interface LibreOffice Base ; elle utilise une connexion ODBC vers le fichier SQLite. Le script n'a besoin ni de LibreOffice ni du pilote ODBC.

Les tables `recette`, `ingredient`, `recette_ingredient`, `planning_repas` et `avis_recette` restent en place. Une ligne de planning représente un jour et un type de repas ; elle contient notamment la recette, la présence et les portions prévues.

## Étapes du traitement

```text
regles.toml + cookBook
          |
    principal.py
          |
    generer_menu.py       Tirage et vérification des recettes
          |
    appliquer_menu.py    Affectation aux repas et historique SQLite
          |
    exporter_courses.py  SELECT sur vue_liste_courses
          |
    generer_site.py      Rendu HTML depuis templates/index.html
          |
    cookBook + menus/historique.json + docs/
```

`principal.py` importe les fonctions des autres scripts. Git est géré par le workflow, pas par le programme Python : une exécution locale ne pousse jamais de modifications.

## Sélection des recettes

Les recettes sont réparties selon les valeurs exactes `Végétarien` et `Non végétarien`. Une catégorie manquante ou différente ne participe pas au tirage. Les recettes affectées aux petits-déjeuners sont exclues des candidates, indépendamment des présences. Les recettes inactives sont exclues lorsque la règle correspondante est activée.

Avec les règles initiales, cinq recettes végétariennes et deux non végétariennes sont tirées sans remise puis mélangées. Une recette peut revenir la semaine suivante. Si le planning complet est identique à celui de la semaine précédente, deux jours différents sont échangés. Lorsque les règles autorisent les répétitions et qu'une seule recette est admissible, un changement de planning n'est pas forcément possible.

Les présences, portions, commentaires et petits-déjeuners ne sont jamais modifiés par la génération. Les quatorze créneaux déjeuner/dîner doivent déjà exister ; un créneau manquant provoque une erreur, sans création implicite de présence.

## Passage entre les semaines

La semaine est identifiée par sa date de lundi, calculée dans le fuseau `Europe/Paris`.

Deux tables sont ajoutées lors de la première génération :

- `menu_semaine` : une entrée par lundi, avec les sept identifiants de dîners, la recette du lundi midi, les règles utilisées et la date de création.
- `menu_courant` : la semaine représentée dans le planning hebdomadaire actuel.

Le lundi midi reprend le dimanche soir de l'historique précédent. Lors de la toute première génération, le dimanche soir du planning existant sert de point de départ : vérifier qu'il représente bien le dimanche précédent.

Le nouveau dimanche soir reste enregistré dans l'historique pour le lundi suivant. Il ne remplace pas le déjeuner du lundi courant. Une semaine manquante dans un historique déjà commencé provoque une erreur explicite, plutôt que d'inventer les restes du lundi. Voir la procédure de rattrapage dans [Utilisation](utilisation.md).

`menus/historique.json` est un export de ces tables. Il n'est jamais utilisé comme source pour le prochain tirage : modifier le JSON ne modifie pas le menu.

## Courses et portions

`vue_liste_courses` reste la source du calcul : repas présents, quantités des ingrédients, portions, stock et prix. Python ne duplique aucun de ces calculs. Le CSV reprend toutes les colonnes de la vue. La page affiche les quantités à acheter et les totaux calculés à partir des coûts de la vue.

Cette vue représente les besoins des **repas consommés dans le planning courant**. Elle ne constitue pas un suivi des lots préparés ou des restes stockés : elle inclut le lundi midi courant et pas le lundi suivant. Les stocks doivent être renseignés selon ton usage habituel ; aucun stock n'est consommé automatiquement.

`vue_repas_soir` est ajustée pour inclure les portions du lundi suivant dans le dîner du dimanche, même si le lundi courant a une autre recette. Faute de planning daté des présences/portions futures, les portions du lundi courant servent de modèle pour le lundi suivant. Cette vue et `vue_ingredients_repas_soir` sont des aides à la préparation ; elles ne modifient pas le calcul des courses.

## Transactions et sauvegardes

Le programme sauvegarde la base avec l'API SQLite dans `backups/`. Il effectue les modifications et le rendu des exports dans une transaction. Une erreur pendant le tirage, la mise à jour ou le rendu annule les modifications SQLite et conserve les anciens exports.

Les nouveaux exports sont préparés dans un dossier temporaire. Après validation de la transaction, les fichiers sont remplacés individuellement. Un incident disque à ce dernier stade peut laisser les exports désynchronisés ; relancer `publier` les reconstruit depuis la base validée. SQLite et le système de fichiers ne forment pas une transaction commune.

Les sauvegardes sont locales, ignorées par Git et ne sont pas publiées. Sur un runner GitHub, elles disparaissent après le job ; la version précédente de la base reste accessible dans l'historique Git de `menus`. Les sauvegardes locales ne sont pas supprimées automatiquement.

## Site

`templates/index.html` contient le modèle, le CSS et le JavaScript. Les textes provenant de la base sont échappés avant insertion dans le HTML. Les liens sont relatifs pour fonctionner à l'adresse du projet GitHub Pages.

Les cases cochées sont conservées dans `localStorage`, par semaine et par nom d'ingrédient. Elles ne modifient ni les stocks ni la base, et ne sont pas synchronisées entre appareils. Si le navigateur bloque le stockage, les coches fonctionnent pour la session mais ne sont pas conservées. Une nouvelle semaine dispose de nouvelles coches.
