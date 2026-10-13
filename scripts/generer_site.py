"""Rendu HTML échappé à partir du planning et de la vue des courses."""

from datetime import date, datetime, timedelta
from html import escape
from string import Template
from zoneinfo import ZoneInfo

from commun import JOURS, RACINE


def nombre(valeur):
    return f"{float(valeur):.2f}".rstrip("0").rstrip(".").replace(".", ",")


def generer_site(connexion, courses, semaine, destination, modele=RACINE / "templates/index.html"):
    planning = {(r["jour_repas"], r["type_repas"]): dict(r) for r in connexion.execute("""
        SELECT p.*, r.nom, r.type_alimentaire FROM planning_repas p
        LEFT JOIN recette r ON r.id_recette=p.id_recette
    """)}
    debut = date.fromisoformat(semaine)
    cartes = []
    for i, jour in enumerate((*JOURS, "Lundi")):
        repas = []
        categories = (("Dejeuner", "Déjeuner"), ("Diner", "Dîner"))
        if i == 0:
            categories = (("Diner", "Dîner"),)
        elif i == 7:
            categories = (("Dejeuner", "Déjeuner · restes du dimanche"),)
        for categorie, libelle in categories:
            r = planning.get((jour, categorie))
            if not r:
                raise ValueError(f"Créneau manquant : {jour} {categorie}.")
            nom = escape(r["nom"] or "Non renseigné")
            statut = "" if r["present"] else '<span class="absent">Absent · hors courses</span>'
            badge = '<span class="badge">Non végétarien</span>' if r["type_alimentaire"] == "Non végétarien" else ""
            repas.append(f'<div class="repas"><span class="label">{libelle}</span><p>{nom}</p>{badge}{statut}</div>')
        cartes.append(f'<article class="jour"><h3>{jour} <small>{(debut + timedelta(days=i)).strftime("%d/%m")}</small></h3>{"".join(repas)}</article>')
    lignes = []
    for i, r in enumerate(courses):
        detail = ""
        if r["quantite_conditionnement"] is not None:
            detail = (f'<small class="secondaire">{r["nombre_conditionnements"]} lot(s) de '
                      f'{nombre(r["quantite_conditionnement"])} {escape(r["unite"])} · '
                      f'besoin après stock : {nombre(r["quantite_manquante"])} {escape(r["unite"])}</small>')
        lignes.append(
            f'<li><label for="achat-{i}"><input id="achat-{i}" type="checkbox" data-ingredient="{escape(r["ingredient"], quote=True)}">'
            f'<span class="ingredient">{escape(r["ingredient"])}{detail}</span>'
            f'<span class="quantite">{nombre(r["quantite_a_acheter"])} {escape(r["unite"])}</span></label></li>'
        )
    prix_estime = sum(r["cout_estime"] or 0 for r in courses)
    prix_magasin = sum(r["cout_reel"] or 0 for r in courses)
    manquants_estime = sum(r["cout_estime"] is None for r in courses)
    manquants_magasin = sum(r["cout_reel"] is None for r in courses)
    couverture = []
    if manquants_estime:
        couverture.append(f"Estimation incomplète : {manquants_estime} tarif(s) manquant(s).")
    if manquants_magasin:
        couverture.append(f"Total magasin incomplet : {manquants_magasin} tarif(s) manquant(s).")
    maintenant = datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %H:%M")
    contenu = Template(modele.read_text(encoding="utf-8")).substitute(
        semaine=semaine,
        periode=f'{debut.strftime("%d/%m/%Y")} au {(debut + timedelta(days=7)).strftime("%d/%m/%Y")}',
        actualisation=maintenant,
        menu="\n".join(cartes),
        courses="\n".join(lignes) or '<li class="vide">Aucun achat nécessaire selon les présences et le stock renseignés.</li>',
        couverture_prix=" ".join(couverture) or "Tous les achats ont un tarif renseigné.",
        cout_estime=nombre(prix_estime), cout_magasin=nombre(prix_magasin),
        nombre_articles=len(courses),
    )
    destination.write_text(contenu, encoding="utf-8")
