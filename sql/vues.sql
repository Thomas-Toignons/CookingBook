-- Sauvegarde des vues SQLite de la base cookBook.
-- Restauration : exécuter ce fichier sur une base contenant déjà les tables.
-- Les vues du même nom sont remplacées ; les données des tables sont conservées.

BEGIN TRANSACTION;

DROP VIEW IF EXISTS "vue_ingredients_repas_soir";
DROP VIEW IF EXISTS "vue_repas_soir";
DROP VIEW IF EXISTS "vue_recette_ingredients";
DROP VIEW IF EXISTS "vue_liste_courses";

CREATE VIEW vue_liste_courses AS
WITH besoins AS (
    SELECT
        ri.id_ingredient,
        SUM(
            ri.quantite_reference * 1.0
            * p.portions_prevues / r.portions_reference
        ) AS quantite_necessaire
    FROM planning_repas AS p
    JOIN recette AS r
        ON r.id_recette = p.id_recette
    JOIN recette_ingredient AS ri
        ON ri.id_recette = r.id_recette
    WHERE p.present = 1
    GROUP BY ri.id_ingredient
),
courses AS (
    SELECT
        i.nom AS ingredient,
        i.unite_reference AS unite,
        b.quantite_necessaire,
        i.stock_quantite,
        MAX(0, b.quantite_necessaire - i.stock_quantite) AS quantite_a_acheter,
        i.base_tarifaire,
        i.prix_estime,
        i.prix_magasin
    FROM besoins AS b
    JOIN ingredient AS i
        ON i.id_ingredient = b.id_ingredient
)
SELECT
    ingredient,
    unite,
    quantite_necessaire,
    stock_quantite,
    quantite_a_acheter,
    COALESCE(ROUND(quantite_a_acheter / base_tarifaire * prix_estime, 2), 0) AS cout_estime,
    COALESCE(ROUND(quantite_a_acheter / base_tarifaire * prix_magasin, 2), 0) AS cout_reel
FROM courses
WHERE quantite_a_acheter > 0
ORDER BY ingredient COLLATE NOCASE;

CREATE VIEW vue_recette_ingredients AS
SELECT
    ri.id_recette_ingredient,
    ri.id_recette,
    ri.id_ingredient,
    i.nom AS ingredient,
    ri.quantite_reference AS quantite,
    i.unite_reference AS unite,
    ri.note
FROM recette_ingredient AS ri
JOIN ingredient AS i
    ON i.id_ingredient = ri.id_ingredient;

CREATE VIEW vue_repas_soir AS
WITH jours (jour, lendemain) AS (
    VALUES
        ('Lundi',    'Mardi'),
        ('Mardi',    'Mercredi'),
        ('Mercredi','Jeudi'),
        ('Jeudi',    'Vendredi'),
        ('Vendredi', 'Samedi'),
        ('Samedi',   'Dimanche'),
        ('Dimanche', 'Lundi')
)
SELECT
    soir.jour_repas AS jour_semaine,
    r.nom AS recette_soir,
    soir.id_recette,
    soir.portions_prevues
        + COALESCE(midi.portions_prevues, 0)
        AS nombre_portions
FROM planning_repas AS soir
JOIN jours AS j
    ON j.jour = soir.jour_repas
LEFT JOIN recette AS r
    ON r.id_recette = soir.id_recette
LEFT JOIN planning_repas AS midi
    ON midi.jour_repas = j.lendemain
    AND midi.type_repas = 'Dejeuner'
    AND midi.id_recette = soir.id_recette
WHERE soir.type_repas = 'Diner';

CREATE VIEW vue_ingredients_repas_soir AS
SELECT
    v.jour_semaine,
    v.id_recette,
    v.nombre_portions,
    i.id_ingredient,
    i.nom AS ingredient,
    ri.quantite_reference * 1.0
        * v.nombre_portions / r.portions_reference
        AS quantite,
    i.unite_reference AS unite
FROM vue_repas_soir AS v
JOIN recette AS r
    ON r.id_recette = v.id_recette
JOIN recette_ingredient AS ri
    ON ri.id_recette = v.id_recette
JOIN ingredient AS i
    ON i.id_ingredient = ri.id_ingredient;

COMMIT;
