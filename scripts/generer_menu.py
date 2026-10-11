"""Tirage des dîners, sans consulter les présences ou les portions."""

import json
import random

from commun import ouvrir_base, lire_regles, lundi_de, options_communes


def valider_diners(connexion, diners, regles):
    if len(diners) != 7:
        raise ValueError("Le menu doit contenir sept dîners.")
    if regles["menu"]["recettes_distinctes"] and len(set(diners)) != 7:
        raise ValueError("Les sept dîners doivent être distincts.")
    recettes = {r["id_recette"]: r for r in connexion.execute("SELECT * FROM recette")}
    petits_dejeuners = {r[0] for r in connexion.execute(
        "SELECT id_recette FROM planning_repas WHERE type_repas = 'Petit-dejeuner'")}
    non_vege = 0
    for identifiant in diners:
        recette = recettes.get(identifiant)
        if recette is None or identifiant in petits_dejeuners:
            raise ValueError(f"Recette de dîner inadmissible : {identifiant}.")
        if regles["selection"]["recettes_actives_uniquement"] and not recette["actif"]:
            raise ValueError(f"Recette désactivée : {recette['nom']}.")
        if recette["type_alimentaire"] not in ("Végétarien", "Non végétarien"):
            raise ValueError(f"Type alimentaire non reconnu : {recette['nom']}.")
        non_vege += recette["type_alimentaire"] == "Non végétarien"
    if non_vege != regles["menu"]["nombre_non_vegetariens"]:
        raise ValueError("Le nombre de dîners non végétariens ne respecte pas les règles.")


def generer_menu(connexion, regles, precedent=None, rng=None):
    rng = rng or random.SystemRandom()
    recettes = list(connexion.execute("""
        SELECT id_recette, type_alimentaire FROM recette
        WHERE (? = 0 OR actif = 1)
          AND id_recette NOT IN (
            SELECT id_recette FROM planning_repas
            WHERE type_repas = 'Petit-dejeuner' AND id_recette IS NOT NULL
          )
        ORDER BY id_recette
    """, (regles["selection"]["recettes_actives_uniquement"],)))
    groupes = {
        categorie: [r["id_recette"] for r in recettes if r["type_alimentaire"] == categorie]
        for categorie in ("Végétarien", "Non végétarien")
    }
    n = regles["menu"]["nombre_non_vegetariens"]
    diners = []
    for categorie, nombre in (("Végétarien", 7 - n), ("Non végétarien", n)):
        disponibles = groupes[categorie]
        minimum = nombre if regles["menu"]["recettes_distinctes"] else int(nombre > 0)
        if len(disponibles) < minimum:
            raise ValueError(f"Recettes {categorie} insuffisantes : {len(disponibles)}, minimum {minimum}.")
        if nombre:
            diners.extend(rng.sample(disponibles, nombre) if regles["menu"]["recettes_distinctes"]
                          else rng.choices(disponibles, k=nombre))
    rng.shuffle(diners)
    if diners == precedent:
        # Un échange suffit à changer l'ordre sans compromettre les contraintes.
        autre = next((i for i in range(1, 7) if diners[i] != diners[0]), None)
        if autre is not None:
            diners[0], diners[autre] = diners[autre], diners[0]
    valider_diners(connexion, diners, regles)
    return diners


if __name__ == "__main__":
    args = options_communes("Prévisualiser un tirage sans modifier la base.").parse_args()
    with ouvrir_base(args.base) as connexion:
        diners = generer_menu(connexion, lire_regles(args.regles))
    print(json.dumps({"semaine": lundi_de(args.semaine).isoformat(), "diners": diners}, indent=2))
