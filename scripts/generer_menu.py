"""Tirage indépendant des présences, avec un conditionnement par viande prévue."""

import json
import random

from commun import ouvrir_base, lire_regles, lundi_de, options_communes
from viandes import recettes_poisson, tirer_non_vegetariens, verifier_viandes


def valider_diners(connexion, diners, regles):
    if len(diners) != 7:
        raise ValueError("Le menu doit contenir sept dîners.")
    if regles["menu"]["recettes_distinctes"] and len(set(diners)) != 7:
        raise ValueError("Les sept dîners doivent être distincts.")
    recettes = {r["id_recette"]: r for r in connexion.execute("SELECT * FROM recette")}
    poissons = recettes_poisson(connexion)
    non_vege = 0
    bonus = 0
    for identifiant in diners:
        recette = recettes.get(identifiant)
        if recette is None or recette["categorie_repas"] != "Dejeuner/Diner":
            raise ValueError(f"Recette de dîner inadmissible : {identifiant}.")
        if regles["selection"]["recettes_actives_uniquement"] and not recette["actif"]:
            raise ValueError(f"Recette désactivée : {recette['nom']}.")
        if recette["type_alimentaire"] not in ("Végétarien", "Non végétarien"):
            raise ValueError(f"Type alimentaire non reconnu : {recette['nom']}.")
        if recette['type_alimentaire'] == 'Non végétarien':
            if identifiant in poissons:
                bonus += 1
            else:
                non_vege += 1
    if non_vege != regles["menu"]["nombre_non_vegetariens"]:
        raise ValueError("Le nombre de dîners non végétariens hors poisson ne respecte pas les règles.")
    if bonus > 1:
        raise ValueError("Un seul dîner de poisson supplémentaire est autorisé.")
    verifier_viandes(connexion, diners, regles)


def generer_menu(connexion, regles, precedent=None, rng=None):
    rng = rng or random.SystemRandom()
    poissons = recettes_poisson(connexion)
    recettes = list(connexion.execute("""
        SELECT id_recette, type_alimentaire FROM recette
        WHERE (? = 0 OR actif = 1)
          AND categorie_repas = 'Dejeuner/Diner'
        ORDER BY id_recette
    """, (regles["selection"]["recettes_actives_uniquement"],)))
    groupes = {categorie: [] for categorie in ('Végétarien', 'Non végétarien', 'Poisson')}
    for r in recettes:
        categorie = r['type_alimentaire']
        if categorie == 'Non végétarien' and r['id_recette'] in poissons:
            categorie = 'Poisson'
        if categorie in groupes:
            groupes[categorie].append(r['id_recette'])
    n = regles['menu']['nombre_non_vegetariens']
    distinctes = regles['menu']['recettes_distinctes']
    minimum_vege = 7 - n - int(bool(groupes['Poisson']) and n < 7)
    for categorie, nombre in (('Végétarien', minimum_vege), ('Non végétarien', n)):
        minimum = nombre if distinctes else int(nombre > 0)
        if len(groupes[categorie]) < minimum:
            raise ValueError(f"Recettes {categorie} insuffisantes : {len(groupes[categorie])}, minimum {minimum}.")
    bonus = 0
    if groupes['Poisson'] and n < 7:
        # Le poisson remplace un dîner végétarien et s'ajoute au quota principal.
        bonus = rng.choice((0, 1))
        if distinctes and len(groupes['Végétarien']) < 7 - n:
            bonus = 1
        elif not groupes['Végétarien'] and 7 - n == 1:
            bonus = 1
    nombre_vege = 7 - n - bonus
    diners = tirer_non_vegetariens(connexion, regles, groupes['Non végétarien'], rng)
    if nombre_vege:
        disponibles = groupes['Végétarien']
        diners.extend(rng.sample(disponibles, nombre_vege) if distinctes
                      else rng.choices(disponibles, k=nombre_vege))
    if bonus:
        diners.append(rng.choice(groupes['Poisson']))
    rng.shuffle(diners)
    if diners == precedent:
        autre = next((i for i in range(1, 7) if diners[i] != diners[0]), None)
        if autre is not None:
            diners[0], diners[autre] = diners[autre], diners[0]
    valider_diners(connexion, diners, regles)
    return diners


if __name__ == '__main__':
    args = options_communes('Prévisualiser un tirage sans modifier la base.').parse_args()
    with ouvrir_base(args.base) as connexion:
        diners = generer_menu(connexion, lire_regles(args.regles))
    print(json.dumps({'semaine': lundi_de(args.semaine).isoformat(), 'diners': diners}, indent=2))
