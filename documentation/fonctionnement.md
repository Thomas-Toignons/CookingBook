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

## Une seule branche de travail

Le code, la base et les exports sont conservés sur `main`. La branche `menus` n'est plus utilisée ; le dossier `menus/` reste le dossier d'export JSON de l'historique.

Le workflow se déclenche le lundi après-midi pour générer le menu. Les pushes de la base, du fichier LibreOffice, des règles, des scripts, du modèle, des vues SQL ou du workflow déclenchent une actualisation des courses et du site. Les pushes de documentation seule n'ont pas besoin de republier le site.

Lors d'un push, le mode `automatique` conserve le menu courant. La seule exception est l'initialisation, lorsqu'aucun menu daté n'existe : il génère alors le premier menu. Le workflow pousse ensuite les résultats sur `main` avec `GITHUB_TOKEN`, ce qui ne déclenche pas un nouveau workflow de push. Le déploiement est réalisé dans la même exécution.

Les exécutions partagent une file et récupèrent le dernier état de `main` au démarrage. Les pushes ne sont jamais forcés ; un changement concurrent de `main` fait échouer le push automatique plutôt que d'écraser des données. Un `git pull` avant les modifications manuelles est indispensable pour récupérer notamment le menu du lundi.

## Sélection des recettes

Les recettes sont réparties selon les valeurs exactes `Végétarien` et `Non végétarien`. Une catégorie manquante ou différente ne participe pas au tirage. Les recettes affectées aux petits-déjeuners sont exclues des candidates, indépendamment des présences. Les recettes inactives sont exclues lorsque la règle correspondante est activée.

Avec les règles initiales, cinq recettes végétariennes et deux non végétariennes sont tirées sans remise puis mélangées. Une recette peut revenir la semaine suivante. Si le planning complet est identique à celui de la semaine précédente, deux jours différents sont échangés. Lorsque les règles autorisent les répétitions et qu'une seule recette est admissible, un changement de planning n'est pas forcément possible.

Les présences, portions, commentaires et petits-déjeuners ne sont jamais modifiés par la génération. Les quatorze créneaux déjeuner/dîner doivent déjà exister ; un créneau manquant provoque une erreur, sans création implicite de présence.

## Période du planning

La semaine est identifiée par la date de son lundi, dans le fuseau `Europe/Paris`. La génération automatique est programmée le lundi à 7 h.

Les déjeuners/dîners couvrent le lundi soir jusqu'au lundi midi suivant. Par exemple, le planning du 12 octobre se termine par le déjeuner du 19 octobre. Dans LibreOffice, « Lundi / Dejeuner » désigne ce dernier repas ; les autres créneaux gardent leurs jours habituels. Les petits-déjeuners restent gérés séparément selon leurs présences.

Lorsque `dejeuner_identique_au_diner_precedent` est activé, mardi midi reprend lundi soir, et lundi midi suivant reprend dimanche soir. Chaque planning est indépendant du précédent. Un nouveau tirage réaffecte aussi le lundi midi suivant. Si la règle est désactivée, les déjeuners manuels restent en place.

`menu_semaine` conserve les dîners, la recette du lundi midi, les règles et la date de génération. Son champ `periode` distingue les archives anciennes (`lundi_courant`) du nouveau fonctionnement (`lundi_suivant`). Seul le planning courant est converti lors de la migration ; les anciennes semaines restent interprétables. `menu_courant` identifie le planning affiché. L'export JSON n'est jamais une source de calcul.

## Courses, portions et conditionnements

`vue_liste_courses` additionne les portions des repas avec `present = 1`, puis retire le stock disponible. Dimanche soir et lundi midi suivant comptent chacun leurs portions selon leur présence. Les vues de préparation utilisent également les présences et n'ajoutent le déjeuner que s'il a la même recette que le dîner.

`ingredient.quantite_conditionnement` est facultatif : NULL conserve l'achat exact du manque ; une valeur positive impose des multiples de ce conditionnement. Elle doit utiliser `unite_reference` (g, ml ou piece), notamment le poids égoutté pour les ingrédients égouttés.

Exemple : besoin de 1600 g, stock de 800 g, lot de 1200 g → manque de 800 g, achat de 1200 g. Un stock suffisant ne déclenche aucun achat. Les coûts sont calculés sur la quantité achetée avec les tarifs existants (`quantite_a_acheter / base_tarifaire * prix`). Les tarifs doivent donc correspondre à cette base tarifaire, et non forcément au prix d'un paquet. Les prix manquants donnent NULL et le site signale les totaux incomplets.

Le formulaire « Ingredients » permet de saisir le conditionnement. Le CSV conserve les quantités nécessaires, le stock, le manque, le conditionnement, le nombre de lots et la quantité à acheter. Le site affiche les lots et le manque après stock. Les achats et les surplus ne modifient jamais automatiquement le stock.

La migration du schéma et des vues est transactionnelle et fonctionne en génération comme en publication. Après la première migration, publier conserve les recettes et les présences manuelles.

## Transactions et sauvegardes

Le programme sauvegarde la base avec l'API SQLite dans `backups/`. Il effectue les modifications et le rendu des exports dans une transaction. Une erreur pendant le tirage, la mise à jour ou le rendu annule les modifications SQLite et conserve les anciens exports.

Les nouveaux exports sont préparés dans un dossier temporaire. Après validation de la transaction, les fichiers sont remplacés individuellement. Un incident disque à ce dernier stade peut laisser les exports désynchronisés ; relancer `publier` les reconstruit depuis la base validée. SQLite et le système de fichiers ne forment pas une transaction commune.

Les sauvegardes sont locales, ignorées par Git et ne sont pas publiées. Sur un runner GitHub, elles disparaissent après le job ; la version précédente de la base reste accessible dans l'historique Git de `main`. Les sauvegardes locales ne sont pas supprimées automatiquement.

## Site

`templates/index.html` contient le modèle, le CSS et le JavaScript. Les textes provenant de la base sont échappés avant insertion dans le HTML. Les liens sont relatifs pour fonctionner à l'adresse du projet GitHub Pages.

Les cases cochées sont conservées dans `localStorage`, par semaine et par nom d'ingrédient. Elles ne modifient ni les stocks ni la base, et ne sont pas synchronisées entre appareils. Si le navigateur bloque le stockage, les coches fonctionnent pour la session mais ne sont pas conservées. Une nouvelle semaine dispose de nouvelles coches.
