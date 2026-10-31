"""Configuration et accès SQLite communs aux commandes."""

import argparse
import sqlite3
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parents[1]
JOURS = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")


def preparer_categories(connexion):
    """Classer une seule fois les recettes d'une ancienne base."""
    colonnes = {r[1] for r in connexion.execute("PRAGMA table_info(recette)")}
    if "categorie_repas" not in colonnes:
        connexion.execute("""ALTER TABLE recette ADD COLUMN categorie_repas TEXT
            NOT NULL DEFAULT 'Dejeuner/Diner'
            CHECK(categorie_repas IN ('Petit-Dej', 'Dejeuner/Diner'))""")
        connexion.execute("""UPDATE recette SET categorie_repas = 'Petit-Dej'
            WHERE id_recette IN (SELECT id_recette FROM planning_repas
                                WHERE type_repas = 'Petit-dejeuner')""")


def lundi_de(semaine=None):
    jour = date.fromisoformat(semaine) if semaine else datetime.now(ZoneInfo("Europe/Paris")).date()
    return jour - timedelta(days=jour.weekday())


def lire_regles(chemin):
    with Path(chemin).open("rb") as fichier:
        regles = tomllib.load(fichier)
    attendus = {
        "menu": {"nombre_non_vegetariens": int, "recettes_distinctes": bool,
                 "dejeuner_identique_au_diner_precedent": bool},
        "selection": {"recettes_actives_uniquement": bool},
    }
    if set(regles) != set(attendus):
        raise ValueError("Sections attendues dans le TOML : menu et selection.")
    for section, champs in attendus.items():
        if set(regles[section]) != set(champs):
            raise ValueError(f"Champs attendus dans [{section}] : {', '.join(champs)}.")
        for champ, type_attendu in champs.items():
            if type(regles[section][champ]) is not type_attendu:
                raise ValueError(f"Type incorrect pour {section}.{champ}.")
    if not 0 <= regles["menu"]["nombre_non_vegetariens"] <= 7:
        raise ValueError("nombre_non_vegetariens doit être compris entre 0 et 7.")
    return regles


def ouvrir_base(chemin):
    # mode=rw interdit la création silencieuse d'une base vide en cas de faute de chemin.
    connexion = sqlite3.connect(Path(chemin).resolve().as_uri() + "?mode=rw", uri=True)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    return connexion


def options_communes(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--base", type=Path, default=RACINE / "cookBook")
    parser.add_argument("--regles", type=Path, default=RACINE / "regles.toml")
    parser.add_argument("--semaine", help="Date ISO, ramenée au lundi de sa semaine (heure de Paris par défaut).")
    return parser
