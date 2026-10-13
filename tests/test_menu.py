"""Tests d'intégration sur une base temporaire, indépendante des données personnelles."""

import json
import random
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "scripts"))
from appliquer_menu import appliquer_menu
from commun import JOURS, lire_regles, ouvrir_base
from generer_menu import generer_menu
from principal import executer


class MenuTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self.tmp.name)
        self.base = self.dossier / "cookBook"
        self.config = self.dossier / "regles.toml"
        self.config.write_text('[menu]\nnombre_non_vegetariens = 2\nrecettes_distinctes = true\ndejeuner_identique_au_diner_precedent = true\n[selection]\nrecettes_actives_uniquement = true\n')
        with sqlite3.connect(self.base) as cible:
            cible.executescript((RACINE / "tests/fixtures.sql").read_text())
            cible.executemany("INSERT INTO recette (id_recette, nom, type_alimentaire, portions_reference, actif) VALUES (?, ?, ?, 2, ?)", [
                (i, f"Recette {i}", "Végétarien" if i <= 8 else "Non végétarien", int(i != 12))
                for i in range(1, 13)
            ])
            cible.execute("INSERT INTO ingredient VALUES (1, 'Riz', 'g', 50, 1000, 2, 3)")
            cible.executemany("INSERT INTO recette_ingredient VALUES (?, ?, 1, 200, NULL)",
                             [(i, i) for i in range(1, 13)])
            cible.executemany("INSERT INTO planning_repas VALUES (?, ?, ?, ?, ?, 1, NULL)", [
                (i * 3 + k + 1, jour, repas, 1 if k == 0 else 9,
                 int(jour not in ("Vendredi", "Samedi")))
                for i, jour in enumerate(JOURS)
                for k, repas in enumerate(("Petit-dejeuner", "Dejeuner", "Diner"))
            ])
            cible.executescript((RACINE / "sql/vues.sql").read_text())
        self.c = ouvrir_base(self.base)
        self.regles = lire_regles(self.config)
        # Les tests fixent les règles métier initiales indépendamment des futures personnalisations.
        self.regles["menu"] = {"nombre_non_vegetariens": 2, "recettes_distinctes": True,
                               "dejeuner_identique_au_diner_precedent": True}
        self.regles["selection"]["recettes_actives_uniquement"] = True

    def tearDown(self):
        self.c.close()
        self.tmp.cleanup()

    def appliquer(self, semaine="2026-10-12", nouveau=False):
        with self.c:
            self.c.execute("BEGIN IMMEDIATE")
            return appliquer_menu(self.c, date.fromisoformat(semaine), self.regles, nouveau, random.Random(42))

    def diners(self):
        return [self.c.execute("SELECT id_recette FROM planning_repas WHERE jour_repas=? AND type_repas='Diner'", (j,)).fetchone()[0] for j in JOURS]

    def test_contraintes_et_preservation(self):
        vue = self.c.execute("SELECT sql FROM sqlite_master WHERE name='vue_liste_courses'").fetchone()[0]
        avant = list(self.c.execute("SELECT id_planning,present,portions_prevues,commentaire FROM planning_repas ORDER BY id_planning"))
        petit = list(self.c.execute("SELECT * FROM planning_repas WHERE type_repas='Petit-dejeuner' ORDER BY id_planning"))
        self.appliquer()
        diners = self.diners()
        self.assertEqual(7, len(set(diners)))
        categories = [self.c.execute("SELECT type_alimentaire FROM recette WHERE id_recette=?", (r,)).fetchone()[0] for r in diners]
        self.assertEqual(2, categories.count("Non végétarien"))
        self.assertEqual(avant, list(self.c.execute("SELECT id_planning,present,portions_prevues,commentaire FROM planning_repas ORDER BY id_planning")))
        self.assertEqual(petit, list(self.c.execute("SELECT * FROM planning_repas WHERE type_repas='Petit-dejeuner' ORDER BY id_planning")))
        self.assertEqual(vue, self.c.execute("SELECT sql FROM sqlite_master WHERE name='vue_liste_courses'").fetchone()[0])

    def test_regles_personnalisees(self):
        self.regles["menu"]["nombre_non_vegetariens"] = 0
        self.regles["menu"]["dejeuner_identique_au_diner_precedent"] = False
        avant = list(self.c.execute("SELECT id_recette FROM planning_repas WHERE type_repas='Dejeuner' ORDER BY id_planning"))
        self.appliquer()
        self.assertEqual(avant, list(self.c.execute("SELECT id_recette FROM planning_repas WHERE type_repas='Dejeuner' ORDER BY id_planning")))
        self.assertTrue(all(self.c.execute("SELECT type_alimentaire FROM recette WHERE id_recette=?", (r,)).fetchone()[0] == "Végétarien" for r in self.diners()))
        self.regles["menu"]["recettes_distinctes"] = False
        self.c.execute("UPDATE recette SET actif=0 WHERE type_alimentaire='Végétarien' AND id_recette != 2")
        self.c.commit()
        self.assertEqual([2] * 7, generer_menu(self.c, self.regles, rng=random.Random(1)))

    def test_regles_changees_exigent_nouveau_tirage(self):
        self.appliquer()
        avant = self.diners()
        self.regles["menu"]["nombre_non_vegetariens"] = 3
        with self.assertRaises(ValueError):
            self.appliquer()
        self.assertEqual(avant, self.diners())
        self.appliquer(nouveau=True)
        categories = [self.c.execute("SELECT type_alimentaire FROM recette WHERE id_recette=?", (r,)).fetchone()[0] for r in self.diners()]
        self.assertEqual(3, categories.count("Non végétarien"))

    def test_tirage_ignore_presences(self):
        a = generer_menu(self.c, self.regles, rng=random.Random(3))
        self.c.execute("UPDATE planning_repas SET present=0, portions_prevues=13")
        b = generer_menu(self.c, self.regles, rng=random.Random(3))
        self.assertEqual(a, b)

    def test_continuite_et_relance(self):
        ancien_dimanche = self.c.execute("SELECT id_recette FROM planning_repas WHERE jour_repas='Dimanche' AND type_repas='Diner'").fetchone()[0]
        self.appliquer()
        premier = self.diners()
        for i, jour in enumerate(JOURS):
            midi = self.c.execute("SELECT id_recette FROM planning_repas WHERE jour_repas=? AND type_repas='Dejeuner'", (jour,)).fetchone()[0]
            self.assertEqual(ancien_dimanche if i == 0 else premier[i-1], midi)
        self.appliquer()
        self.assertEqual(premier, self.diners())
        self.appliquer("2026-10-19")
        self.assertEqual(premier[6], self.c.execute("SELECT id_recette FROM planning_repas WHERE jour_repas='Lundi' AND type_repas='Dejeuner'").fetchone()[0])
        self.assertNotEqual(premier, self.diners())

    def test_nouveau_tirage_conserve_lundi(self):
        self.appliquer()
        ancien = self.diners()
        midi = self.c.execute("SELECT lundi_midi FROM menu_semaine").fetchone()[0]
        self.appliquer(nouveau=True)
        self.assertNotEqual(ancien, self.diners())
        self.assertEqual(midi, self.c.execute("SELECT lundi_midi FROM menu_semaine").fetchone()[0])

    def test_dimanche_portions_du_lundi_suivant(self):
        self.c.execute("UPDATE planning_repas SET portions_prevues=3 WHERE jour_repas='Lundi' AND type_repas='Dejeuner'")
        self.c.commit()
        self.appliquer()
        resultat = self.c.execute("SELECT nombre_portions FROM vue_repas_soir WHERE jour_semaine='Dimanche'").fetchone()[0]
        dimanche = self.c.execute("SELECT portions_prevues FROM planning_repas WHERE jour_repas='Dimanche' AND type_repas='Diner'").fetchone()[0]
        self.assertEqual(dimanche + 3, resultat)

    def test_instructions_formulaire_conservees_apres_generation(self):
        self.c.execute("UPDATE recette SET instructions = 'Préparer la recette ' || id_recette")
        self.c.commit()
        for semaine in ("2026-10-12", "2026-10-19"):
            self.appliquer(semaine)
            lignes = self.c.execute("SELECT id_recette, intructions_recette FROM vue_repas_soir").fetchall()
            self.assertEqual(7, len(lignes))
            for ligne in lignes:
                self.assertEqual(f"Préparer la recette {ligne[0]}", ligne[1])

    def test_pas_de_mutation_si_creaneau_manquant(self):
        self.c.execute("DELETE FROM planning_repas WHERE jour_repas='Samedi' AND type_repas='Diner'")
        self.c.commit()
        avant = list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning"))
        with self.assertRaisesRegex(ValueError, "Créneau manquant"):
            self.appliquer()
        self.assertEqual(avant, list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning")))
        self.assertIsNone(self.c.execute("SELECT name FROM sqlite_master WHERE name='menu_semaine'").fetchone())

    def test_insuffisance_et_types_configuration(self):
        self.c.execute("UPDATE recette SET actif=0 WHERE type_alimentaire='Végétarien'")
        with self.assertRaisesRegex(ValueError, "insuffisantes"):
            generer_menu(self.c, self.regles)
        mauvais = self.dossier / "mauvais.toml"
        mauvais.write_text(self.config.read_text().replace("nombre_non_vegetariens = 2", "nombre_non_vegetariens = true"))
        with self.assertRaisesRegex(ValueError, "Type incorrect"):
            lire_regles(mauvais)

    def test_export_et_publication_ne_changent_pas_menu(self):
        sortie, historique = self.dossier / "docs", self.dossier / "menus/historique.json"
        # Écrire la configuration des tests pour ne pas dépendre de futurs réglages du repo.
        config = self.dossier / "regles.toml"
        config.write_text('[menu]\nnombre_non_vegetariens=2\nrecettes_distinctes=true\ndejeuner_identique_au_diner_precedent=true\n[selection]\nrecettes_actives_uniquement=true\n')
        executer("generer", self.base, config, sortie, historique, "2026-10-12")
        avant = self.diners()
        # Les intitulés sont échappés, jamais injectés comme HTML.
        self.c.execute("UPDATE ingredient SET nom='<script>attaque</script>' WHERE id_ingredient=1")
        self.c.execute("UPDATE planning_repas SET present=1")
        self.c.execute("UPDATE ingredient SET stock_quantite=0")
        self.c.commit()
        executer("publier", self.base, config, sortie, historique)
        self.assertEqual(avant, self.diners())
        html = (sortie / "index.html").read_text()
        self.assertNotIn("<script>attaque</script>", html)
        self.assertIn("&lt;script&gt;attaque&lt;/script&gt;", html)
        self.assertEqual(1, len(json.loads(historique.read_text())))
        self.c.execute("UPDATE planning_repas SET present=0")
        self.c.commit()
        executer("publier", self.base, config, sortie, historique)
        self.assertIn("Aucun achat nécessaire", (sortie / "index.html").read_text())
        self.assertEqual(1, len((sortie / "courses.csv").read_text(encoding="utf-8-sig").splitlines()))

    def test_echec_rendu_annule_base_et_conserve_exports(self):
        sortie, historique = self.dossier / "docs", self.dossier / "historique.json"
        sortie.mkdir()
        (sortie / "index.html").write_text("ancienne page")
        avant = list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning"))
        from unittest.mock import patch
        with patch("principal.generer_site", side_effect=ValueError("échec rendu")):
            with self.assertRaisesRegex(ValueError, "échec rendu"):
                executer("generer", self.base, self.config, sortie, historique, "2026-10-12")
        self.assertEqual(avant, list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning")))
        self.assertEqual("ancienne page", (sortie / "index.html").read_text())

    def test_refuse_trou_historique_et_retour_arriere(self):
        self.appliquer()
        with self.assertRaisesRegex(ValueError, "précédente manquante"):
            self.appliquer("2026-10-26")
        with self.assertRaisesRegex(ValueError, "antérieure"):
            self.appliquer("2026-10-05")

    def test_push_initialise_puis_preserve_modifications_manuelles(self):
        from unittest.mock import patch
        sortie, historique = self.dossier / "docs", self.dossier / "historique.json"
        with patch("principal.lundi_de", return_value=date(2026, 10, 12)):
            executer("automatique", self.base, self.config, sortie, historique)
        self.assertEqual("2026-10-12", self.c.execute("SELECT semaine FROM menu_courant").fetchone()[0])
        # Un utilisateur peut changer le planning ; un push ne doit pas réaffecter les recettes.
        self.c.execute("UPDATE planning_repas SET present=0 WHERE type_repas='Diner'")
        self.c.execute("UPDATE planning_repas SET id_recette=2 WHERE jour_repas='Mardi' AND type_repas='Diner'")
        self.c.commit()
        avant = list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning"))
        # Même une semaine plus tard, le push reste une publication, pas une génération.
        with patch("principal.lundi_de", return_value=date(2026, 10, 19)):
            executer("automatique", self.base, self.config, sortie, historique)
        self.assertEqual(avant, list(self.c.execute("SELECT * FROM planning_repas ORDER BY id_planning")))
        self.assertEqual(1, self.c.execute("SELECT COUNT(*) FROM menu_semaine").fetchone()[0])

    def test_automatique_refuse_options_de_tirage(self):
        with self.assertRaisesRegex(ValueError, "Seul le mode generer"):
            executer("automatique", self.base, self.config, self.dossier / "docs",
                     self.dossier / "historique.json", nouveau_tirage=True)


if __name__ == "__main__":
    unittest.main()
