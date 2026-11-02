"""Quantités de référence prévues, indépendantes du planning et du stock."""

from itertools import combinations, combinations_with_replacement
from math import isclose


def charger_viandes(connexion):
    colonnes = {r[1] for r in connexion.execute("PRAGMA table_info(ingredient)")}
    filtre = "est_viande = 1" if "est_viande" in colonnes else "nom IN ('Poulet', 'Bœuf haché')"
    viandes = list(connexion.execute(f"SELECT * FROM ingredient WHERE {filtre}"))
    quantites = {(r['id_recette'], r['id_ingredient']): r['quantite']
                 for r in connexion.execute("""SELECT id_recette, id_ingredient,
                     SUM(quantite_reference) AS quantite FROM recette_ingredient
                     GROUP BY id_recette, id_ingredient""")}
    return viandes, quantites


def recettes_poisson(connexion):
    """Une recette mêlant viande et poisson reste dans le quota principal."""
    colonnes = {r[1] for r in connexion.execute("PRAGMA table_info(ingredient)")}
    poisson = "i.est_poisson=1" if "est_poisson" in colonnes else "i.nom IN ('Thon au naturel égoutté', 'Filet de poisson blanc')"
    viande = "i.est_viande=1" if "est_viande" in colonnes else "i.nom IN ('Poulet', 'Bœuf haché')"
    return {r[0] for r in connexion.execute(f"""SELECT ri.id_recette
        FROM recette_ingredient ri JOIN ingredient i USING(id_ingredient)
        GROUP BY ri.id_recette
        HAVING MAX({poisson})=1 AND MAX({viande})=0""")}


def verifier_viandes(connexion, diners, regles):
    viandes, quantites = charger_viandes(connexion)
    erreurs = []
    for viande in viandes:
        total = sum(quantites.get((r, viande['id_ingredient']), 0) for r in diners)
        if not total:
            continue
        lot = viande['quantite_conditionnement']
        if lot is None:
            erreurs.append(f"{viande['nom']} : conditionnement manquant")
        elif not isclose(total, lot, rel_tol=0, abs_tol=1e-7):
            erreurs.append(f"{viande['nom']} : {total:g} {viande['unite_reference']} prévus pour un lot de {lot:g}")
    if erreurs:
        raise ValueError("Quantité de viande différente d'un conditionnement : " + "; ".join(erreurs) + ".")


def tirer_non_vegetariens(connexion, regles, disponibles, rng):
    nombre = regles['menu']['nombre_non_vegetariens']
    combiner = combinations if regles['menu']['recettes_distinctes'] else combinations_with_replacement
    candidats = list(disponibles)
    rng.shuffle(candidats)
    # L'ordre des jours ne change pas les quantités de référence prévues.
    for selection in combiner(candidats, nombre):
        try:
            verifier_viandes(connexion, selection, regles)
        except ValueError:
            continue
        return list(selection)
    raise ValueError("Aucun menu possible : la quantité prévue de chaque viande doit être "
                     "égale à un conditionnement, sans tenir compte des présences ni du stock.")
