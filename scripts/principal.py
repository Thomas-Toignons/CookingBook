"""Orchestration locale. Git et le déploiement restent dans GitHub Actions."""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from appliquer_menu import appliquer_menu, exporter_historique, semaine_courante, preparer_schema
from commun import RACINE, lire_regles, lundi_de, ouvrir_base, options_communes
from exporter_courses import exporter_courses, lire_courses
from generer_site import generer_site


def executer(mode, base, regles, sortie, historique, semaine=None, nouveau_tirage=False):
    configuration = lire_regles(regles)
    if mode not in ("generer", "publier", "automatique"):
        raise ValueError(f"Mode inconnu : {mode}.")
    if mode != "generer" and (nouveau_tirage or semaine):
        raise ValueError("Seul le mode generer accepte --semaine ou --nouveau-tirage.")
    sortie, historique = Path(sortie), Path(historique)
    sortie.mkdir(parents=True, exist_ok=True)
    historique.parent.mkdir(parents=True, exist_ok=True)
    connexion = ouvrir_base(base)
    try:
        if mode == "automatique":
            # Les pushes publient le planning existant ; seul le premier initialise
            # un menu daté, avant que la planification du lundi prenne le relais.
            table = connexion.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='menu_courant'").fetchone()
            initialise = table and connexion.execute("SELECT 1 FROM menu_courant WHERE singleton=1").fetchone()
            mode = "publier" if initialise else "generer"
        # Sauvegarde SQLite cohérente, y compris si la base possède un journal WAL.
        sauvegardes = Path(base).resolve().parent / "backups"
        sauvegardes.mkdir(exist_ok=True)
        nom = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        with sqlite3.connect(sauvegardes / f"cookBook-{nom}.sqlite") as copie:
            connexion.backup(copie)
        with tempfile.TemporaryDirectory(prefix="cookingbook-", dir=sortie.parent) as temporaire:
            travail = Path(temporaire)
            connexion.execute("BEGIN IMMEDIATE")
            try:
                if mode == "generer":
                    cle = appliquer_menu(connexion, lundi_de(semaine), configuration, nouveau_tirage)
                else:
                    preparer_schema(connexion)
                    cle = semaine_courante(connexion)
                courses = lire_courses(connexion)
                exporter_courses(courses, travail / "courses.csv")
                generer_site(connexion, courses, cle, travail / "index.html")
                archive = exporter_historique(connexion)
                (travail / "historique.json").write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if connexion.execute("PRAGMA foreign_key_check").fetchone():
                    raise ValueError("La base contient une référence étrangère invalide.")
                connexion.commit()
            except Exception:
                connexion.rollback()
                raise
            # Les fichiers sont construits avant validation de la transaction.
            # Un incident de remplacement après commit se répare avec le mode publier.
            for fichier in ("index.html", "courses.csv"):
                os.replace(travail / fichier, sortie / fichier)
            # Le JSON peut être sur un autre système de fichiers : temporaire voisin.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=historique.parent, delete=False) as fichier:
                fichier.write((travail / "historique.json").read_text(encoding="utf-8"))
                nom_temporaire = fichier.name
            os.replace(nom_temporaire, historique)
        return cle, len(courses)
    finally:
        connexion.close()


def main():
    parser = options_communes("Générer le menu ou actualiser les exports sans refaire le tirage.")
    parser.add_argument("mode", choices=("generer", "publier", "automatique"),
                        help="automatique publie le menu courant ou initialise le premier menu si nécessaire")
    parser.add_argument("--sortie", type=Path, default=RACINE / "docs")
    parser.add_argument("--historique", type=Path, default=RACINE / "menus/historique.json")
    parser.add_argument("--nouveau-tirage", action="store_true", help="Remplacer explicitement le tirage de la semaine.")
    args = parser.parse_args()
    try:
        semaine, articles = executer(args.mode, args.base, args.regles, args.sortie, args.historique,
                                    args.semaine, args.nouveau_tirage)
    except (ValueError, OSError, sqlite3.Error) as erreur:
        parser.exit(1, f"Erreur : {erreur}\n")
    print(f"Semaine du {semaine} : {articles} ingrédients à acheter. Page : {args.sortie / 'index.html'}")


if __name__ == "__main__":
    main()
