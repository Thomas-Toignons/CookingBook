# GitHub Actions, branche menus et publication

## Configuration initiale

1. Pousser le code, `regles.toml`, le modèle, les vues SQL et les workflows sur la branche `main`. `main` doit être la branche par défaut pour la planification.
2. Dans **Settings → Pages → Build and deployment**, choisir **GitHub Actions** comme source.
3. Autoriser le workflow à écrire dans le dépôt. Le job de construction demande `contents: write` ; les politiques du dépôt ou de l'organisation doivent le permettre.
4. Si l'environnement `github-pages` impose des restrictions de branches, autoriser `main`, car c'est la branche d'exécution du workflow, même si les fichiers sont conservés sur `menus`.
5. Dans **Actions → Menu hebdomadaire et courses → Run workflow**, choisir `main`, puis le mode `generer`.

La branche `menus` est créée automatiquement si elle n'existe pas. La première génération utilise le `cookBook` de `main`. Vérifier avant ce premier lancement que le dîner du dimanche y représente le repas précédant la semaine à générer.

Le site sera disponible à l'adresse :

```text
https://thomas-toignons.github.io/CookingBook/
```

Cette adresse est celle attendue pour le dépôt ; le résultat du job de déploiement fournit l'adresse effectivement publiée. Elle n'est active qu'après configuration et déploiement réussis.

GitHub Pages standard publie un site accessible publiquement. Avec GitHub Free, le dépôt source doit être public ; l'utilisation d'un dépôt privé dépend du forfait. Seul `docs/` est envoyé à Pages, mais les fichiers d'un dépôt public restent consultables via GitHub.

Sources officielles : [création d'un site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [publication par workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Déroulement automatique

Le workflow `.github/workflows/menu-hebdomadaire.yml` est programmé chaque lundi à **7 h 15, Europe/Paris**, avec prise en compte du changement d'heure.

Il récupère deux copies du dépôt :

- `source/` sur `main` pour le code, les règles, le modèle et les vues SQL.
- `etat/` sur `menus` pour la base et les résultats ; la branche est initialisée depuis `main` au premier lancement.

Les tests sont exécutés avant le traitement. Le script principal produit le menu et les exports dans `etat/`, puis le workflow enregistre `cookBook`, `menus/historique.json`, `docs/index.html` et `docs/courses.csv` dans un commit. Les sauvegardes ne sont pas poussées.

Le push est normal, jamais forcé : si un changement manuel concurrent arrive sur `menus`, le push échoue plutôt que d'écraser ce changement. Relancer après synchronisation. Les exécutions du workflow sont mises en attente les unes derrière les autres.

Le dossier `docs/` est ensuite envoyé comme artefact Pages, puis déployé par un second job. Un échec de déploiement peut donc survenir après le commit des données ; une relance en mode `publier` permet de reprendre la publication sans changer le menu.

Les workflows planifiés peuvent être retardés ou ne pas s'exécuter en cas de forte charge. Dans un dépôt public, ils peuvent être désactivés après 60 jours d'inactivité. La génération prévoit un diagnostic si une semaine manque dans l'historique. [Documentation des événements planifiés](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Modifier les données manuellement

Après la première génération, la base quotidienne est celle de `menus`. Garder LibreOffice fermé pendant les opérations Git qui remplacent la base.

```bash
git fetch origin
git switch menus
git pull --ff-only origin menus
```

Lors du premier accès local, si la branche n'existe pas encore localement :

```bash
git switch --track origin/menus
```

Ouvrir ensuite `cookingBook.odb` et modifier les présences, portions, stocks, recettes ou ingrédients. Fermer LibreOffice pour enregistrer les modifications, puis :

```bash
git add cookBook
git commit -m "Mettre à jour les présences et les stocks"
git push origin menus
```

Dans **Actions**, lancer **Menu hebdomadaire et courses** depuis `main`, en mode **publier**. Ce mode récupère la base modifiée de `menus`, recalcule les courses et actualise le site sans modifier le menu. Un push manuel sur `menus` ne déclenche pas automatiquement de génération ou de publication.

Pour éviter les changements de branche dans le dossier ouvert par LibreOffice, on peut utiliser deux clones séparés : un pour `main` et un pour `menus`. Adapter alors la connexion ODBC/LibreOffice au chemin de la base du clone `menus` ; le `.odb` actuel contient un chemin absolu local.

## Modifier le code ou les règles

Sur `main`, modifier les scripts, `regles.toml` ou le modèle puis pousser. Le prochain workflow utilisera ces versions directement, même si les copies des scripts présentes sur `menus` sont anciennes. Ne pas fusionner `main` dans `menus` pour actualiser le code : cela pourrait remplacer ou provoquer un conflit sur la base binaire.

Pour une exécution locale avec la dernière version du code et la base de `menus`, utiliser les chemins explicites depuis le clone `main` :

```bash
python3 scripts/principal.py publier \
  --base /chemin/clone-menus/cookBook \
  --sortie /chemin/clone-menus/docs \
  --historique /chemin/clone-menus/menus/historique.json
```

## Relance et nouveau tirage

`generer` réutilise un menu existant de la semaine actuelle. Pour remplacer volontairement ce menu, sélectionner le mode `generer` et cocher **nouveau_tirage**. Ne pas cocher cette option avec `publier`.

Le workflow n'accepte que les lancements depuis `main`. Le workflow séparé `verifications.yml` exécute les tests lors des pushes et pull requests vers `main`.
