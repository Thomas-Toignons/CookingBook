"""Application transactionnelle du menu et historique daté dans SQLite."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from commun import JOURS, RACINE
from generer_menu import generer_menu, valider_diners


def preparer_schema(connexion):
    connexion.execute("""CREATE TABLE IF NOT EXISTS menu_semaine (
        semaine TEXT PRIMARY KEY,
        diners_json TEXT NOT NULL,
        lundi_midi INTEGER REFERENCES recette(id_recette),
        regles_json TEXT NOT NULL,
        genere_le TEXT NOT NULL
    )""")
    connexion.execute("""CREATE TABLE IF NOT EXISTS menu_courant (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        semaine TEXT NOT NULL REFERENCES menu_semaine(semaine)
    )""")
    # Migrer uniquement la vue de préparation du soir ; la vue des courses
    # existante (y compris ses éventuelles personnalisations) reste intacte.
    sql = (RACINE / "sql/vues.sql").read_text(encoding="utf-8")
    instruction = ""
    for ligne in sql.splitlines():
        if ligne.strip().startswith("--"):
            continue
        instruction += ligne + "\n"
        if sqlite3.complete_statement(instruction):
            texte = instruction.strip()
            if texte.startswith(('DROP VIEW IF EXISTS "vue_repas_soir"', 'CREATE VIEW vue_repas_soir AS')):
                connexion.execute(instruction)
            instruction = ""


def appliquer_menu(connexion, semaine, regles, nouveau_tirage=False, rng=None):
    preparer_schema(connexion)
    cle = semaine.isoformat()
    courant = connexion.execute("SELECT semaine FROM menu_courant WHERE singleton = 1").fetchone()
    if courant and cle < courant[0]:
        raise ValueError("Impossible de remplacer le planning courant par une semaine antérieure.")
    precedent = connexion.execute("SELECT * FROM menu_semaine WHERE semaine = ?",
                                 ((semaine - timedelta(days=7)).isoformat(),)).fetchone()
    existant = connexion.execute("SELECT * FROM menu_semaine WHERE semaine = ?", (cle,)).fetchone()
    if existant and not nouveau_tirage:
        diners = json.loads(existant["diners_json"])
        valider_diners(connexion, diners, regles)
        if json.loads(existant["regles_json"]) != regles:
            raise ValueError("Règles modifiées : utiliser --nouveau-tirage pour appliquer la nouvelle configuration.")
        lundi_midi = existant["lundi_midi"]
        genere_le = existant["genere_le"]
    else:
        if existant:
            lundi_midi = existant["lundi_midi"]
        elif precedent:
            lundi_midi = json.loads(precedent["diners_json"])[6]
        elif courant:
            raise ValueError("Semaine précédente manquante. Générer les semaines manquantes dans l'ordre avec --semaine.")
        else:
            dimanche = connexion.execute("SELECT id_recette FROM planning_repas WHERE jour_repas='Dimanche' AND type_repas='Diner'").fetchone()
            if dimanche is None or dimanche[0] is None:
                raise ValueError("Initialisation : renseigner le dîner du dimanche précédent dans le planning.")
            lundi_midi = dimanche[0]
        ancien = json.loads(existant["diners_json"]) if existant else (json.loads(precedent["diners_json"]) if precedent else None)
        diners = generer_menu(connexion, regles, ancien, rng)
        genere_le = datetime.now(timezone.utc).isoformat()
        connexion.execute("""INSERT INTO menu_semaine VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(semaine) DO UPDATE SET diners_json=excluded.diners_json,
            lundi_midi=excluded.lundi_midi, regles_json=excluded.regles_json, genere_le=excluded.genere_le""",
                          (cle, json.dumps(diners), lundi_midi, json.dumps(regles, ensure_ascii=False), genere_le))
    for i, jour in enumerate(JOURS):
        repas = [("Diner", diners[i])]
        if regles["menu"]["dejeuner_identique_au_diner_precedent"]:
            repas.append(("Dejeuner", lundi_midi if i == 0 else diners[i - 1]))
        for type_repas, recette in repas:
            resultat = connexion.execute("UPDATE planning_repas SET id_recette=? WHERE jour_repas=? AND type_repas=?",
                                          (recette, jour, type_repas))
            if resultat.rowcount != 1:
                raise ValueError(f"Créneau manquant dans planning_repas : {jour} {type_repas}.")
    connexion.execute("INSERT INTO menu_courant VALUES (1, ?) ON CONFLICT(singleton) DO UPDATE SET semaine=excluded.semaine", (cle,))
    return cle


def semaine_courante(connexion):
    if not connexion.execute("SELECT 1 FROM sqlite_master WHERE name='menu_courant'").fetchone():
        raise ValueError("Aucun menu daté. Exécuter d'abord le mode generer.")
    ligne = connexion.execute("SELECT semaine FROM menu_courant WHERE singleton=1").fetchone()
    if ligne is None:
        raise ValueError("Aucun menu daté. Exécuter d'abord le mode generer.")
    return ligne[0]


def exporter_historique(connexion):
    return [{"semaine": r["semaine"], "diners": json.loads(r["diners_json"]),
             "lundi_midi": r["lundi_midi"], "regles": json.loads(r["regles_json"]),
             "genere_le": r["genere_le"]}
            for r in connexion.execute("SELECT * FROM menu_semaine ORDER BY semaine")]
