# GitHub Actions et GitHub Pages sur main

## Configuration initiale

1. Utiliser `main` comme branche par défaut. Tout est conservé sur cette branche : code, règles, base et exports.
2. Dans **Settings → Pages → Build and deployment → Source**, choisir **GitHub Actions**. Le workflow existe déjà ; il n'est pas nécessaire d'ajouter un modèle proposé par GitHub.
3. Dans **Settings → Actions → General**, vérifier que GitHub Actions est autorisé. Le workflow demande `contents: write` pour enregistrer la base ; les politiques du dépôt et de l'organisation doivent permettre cette écriture. Aucun secret personnel n'est nécessaire : `GITHUB_TOKEN` est fourni automatiquement.
4. Si `main` est protégée, ses règles doivent permettre au workflow de pousser ses commits. Une obligation de pull request ou de vérifications sur chaque commit peut bloquer cette écriture directe ; adapter les règles du dépôt à ce fonctionnement.
5. Si **Settings → Environments → github-pages** contient des restrictions de branches, autoriser `main`.
6. Vérifier les présences : « Lundi / Dejeuner » désigne le lundi suivant le dimanche du planning. Il reprend la recette de ce dimanche lorsque la liaison des déjeuners est activée.
7. Pousser les changements sur `main`. Ce push déclenche le traitement et le déploiement. Un menu daté existant est conservé ; sinon, le premier menu est généré.

Si le premier push a précédé la configuration de Pages, ou pour reprendre un déploiement échoué, ouvrir **Actions → Menu hebdomadaire et courses → Run workflow**, choisir `main` et `publier` si le menu a déjà été initialisé. Choisir `generer` si aucun menu daté n'existe. Laisser **nouveau_tirage** décoché.

Les jobs `construire` et `deployer` doivent être verts. Le résultat du déploiement fournit l'adresse publiée ; pour ce dépôt, l'adresse attendue est :

```text
https://thomas-toignons.github.io/CookingBook/
```

GitHub Pages standard publie un site public. Avec GitHub Free, le dépôt source doit être public ; la publication depuis un dépôt privé dépend du forfait. Seul `docs/` est envoyé au site. Les fichiers d'un dépôt public restent néanmoins consultables via GitHub.

Sources officielles : [configuration de Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), [publication par workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Ce qui se passe automatiquement

| Déclenchement | Résultat |
| --- | --- |
| Lundi à 14 h 15, `Europe/Paris` | Génération de la semaine, enregistrement de la base et des exports sur `main`, publication Pages. |
| Push de `cookBook` ou `cookingBook.odb` sur `main` | Actualisation des courses et du HTML depuis le planning existant, sans nouveau tirage. |
| Push des règles, scripts, modèle, vues SQL ou du workflow sur `main` | Actualisation du site ; les nouvelles règles prennent effet lors de la prochaine génération. |
| Premier push déclencheur, sans historique daté | Initialisation du premier menu, puis publication. |
| Push de documentation seule | Vérifications Python ; aucune publication nécessaire. |

Les fichiers précis sont déclarés dans `on.push.paths` du workflow `.github/workflows/menu-hebdomadaire.yml`. Le dossier `menus/` contient l'historique JSON ; ce n'est pas une branche.

Le workflow récupère la dernière version de `main`, vérifie les scripts, exécute `principal.py`, puis enregistre uniquement `cookBook`, `menus/historique.json`, `docs/index.html` et `docs/courses.csv`. Les sauvegardes restent ignorées par Git.

Le commit automatique est poussé avec `GITHUB_TOKEN`. Un push effectué avec ce jeton ne déclenche pas une nouvelle exécution de push : aucune boucle. La publication Pages est réalisée directement par le second job de la même exécution. [Documentation des déclenchements](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

Les exécutions sont mises en attente les unes derrière les autres. Un ancien push en attente traite la dernière version de `main` disponible à son démarrage. Le push automatique n'est jamais forcé : un changement concurrent fait échouer ce push, et le site de cette exécution n'est pas déployé.

## Routine quotidienne

Fermer LibreOffice avant les opérations Git qui remplacent la base. Avant les modifications :

```bash
git switch main
git pull --ff-only origin main
```

Ouvrir `cookingBook.odb`, modifier les présences, portions, stocks, ingrédients ou recettes, puis fermer LibreOffice. Ensuite :

```bash
git add cookBook
git commit -m "Actualiser les présences et les stocks"
git push origin main
```

Si les formulaires ou rapports ont aussi changé, ajouter `cookingBook.odb` au commit. GitHub actualise ensuite les courses et le site automatiquement. Aucun script local ou lancement dans Actions n'est requis.

Le lundi, GitHub modifie lui-même la base sur `main`. Le `git pull` avant les prochaines modifications permet de récupérer ce menu. SQLite est un fichier binaire : Git ne fusionne pas proprement deux modifications concurrentes. Si le pull ou le push signale un conflit, conserver une copie de ta base et résoudre la synchronisation ; ne pas utiliser de push forcé pour contourner le problème.

## Changer les règles ou le code

Modifier les fichiers sur `main`, faire le commit et pousser comme pour les données. Un changement de `regles.toml` ne remplace pas le menu de la semaine en cours. Pour appliquer de nouvelles règles immédiatement, utiliser le lancement manuel en mode `generer` avec **nouveau_tirage** coché.

`generer` sans cette option réutilise le menu enregistré. `publier` conserve les recettes après la migration initiale. Cette migration réaffecte une seule fois le lundi midi au dimanche du planning, sans refaire les dîners. Ne pas cocher **nouveau_tirage** avec `publier`.

## Transition depuis l'ancienne branche menus

Si `menus` contient une base plus récente, rapatrier une seule fois ses données sur `main` avant de démarrer la nouvelle automatisation. Ne pas fusionner tout son ancien code avec `main`.

Fermer LibreOffice, conserver une copie de sécurité de `cookBook`, comparer les versions puis récupérer les fichiers de données concernés. Par exemple, si `menus` est bien la version à conserver :

```bash
git fetch origin
git restore --source=origin/menus -- cookBook
```

Récupérer aussi `menus/historique.json` s'il existe, et `cookingBook.odb` uniquement si ses formulaires ou rapports sont plus récents. Faire le commit sur `main` et pousser avec les workflows mis à jour. La branche `menus` peut rester archivée : rien ne la lit ou ne la met à jour désormais.

## Dépannage

- **Workflow absent** : vérifier que le YAML est poussé sur `main` et que Actions est activé.
- **Écriture refusée sur main** : vérifier les politiques Actions et les protections de branche.
- **Déploiement refusé** : vérifier la source Pages et les restrictions de l'environnement `github-pages`.
- **Push automatique refusé après une modification concurrente** : la base distante est préservée. Le workflow de ton nouveau push republiera les dernières données ; si la génération a été interrompue, relancer `generer` après synchronisation.
- **Publication échouée après un commit réussi** : relancer en mode `publier`.
- **Semaine manquante** : voir le rattrapage dans [Utilisation](utilisation.md).

GitHub peut retarder les tâches planifiées ; dans un dépôt public, elles peuvent être désactivées après 60 jours d'inactivité. Le menu n'est donc pas garanti à la minute exacte. [Documentation des événements planifiés](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
