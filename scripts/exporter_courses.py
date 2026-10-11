"""Lecture de la vue existante, sans recalcul des stocks ou des portions."""

import csv
from pathlib import Path

from commun import ouvrir_base, options_communes


def lire_courses(connexion):
    return [dict(r) for r in connexion.execute("SELECT * FROM vue_liste_courses ORDER BY ingredient COLLATE NOCASE")]


def exporter_courses(courses, destination):
    champs = ("ingredient", "unite", "quantite_necessaire", "stock_quantite", "quantite_a_acheter", "cout_estime", "cout_reel")
    with destination.open("w", encoding="utf-8-sig", newline="") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=champs, delimiter=";")
        writer.writeheader()
        writer.writerows(courses)


if __name__ == "__main__":
    parser = options_communes("Exporter la vue des courses, sans modifier le menu.")
    parser.add_argument("--sortie", type=Path, default=Path("courses.csv"))
    args = parser.parse_args()
    with ouvrir_base(args.base) as connexion:
        exporter_courses(lire_courses(connexion), args.sortie)
