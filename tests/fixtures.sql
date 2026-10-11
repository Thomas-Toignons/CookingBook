-- Données de test autonomes : elles ne dépendent pas des recettes personnelles.
CREATE TABLE recette (
    id_recette INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    type_alimentaire TEXT,
    portions_reference REAL NOT NULL CHECK(portions_reference > 0),
    actif INTEGER NOT NULL CHECK(actif IN (0,1))
);
CREATE TABLE ingredient (
    id_ingredient INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    unite_reference TEXT NOT NULL,
    stock_quantite REAL NOT NULL,
    base_tarifaire REAL NOT NULL,
    prix_estime REAL,
    prix_magasin REAL
);
CREATE TABLE recette_ingredient (
    id_recette_ingredient INTEGER PRIMARY KEY,
    id_recette INTEGER NOT NULL REFERENCES recette(id_recette),
    id_ingredient INTEGER NOT NULL REFERENCES ingredient(id_ingredient),
    quantite_reference REAL NOT NULL,
    note TEXT
);
CREATE TABLE planning_repas (
    id_planning INTEGER PRIMARY KEY,
    jour_repas TEXT NOT NULL,
    type_repas TEXT NOT NULL,
    id_recette INTEGER REFERENCES recette(id_recette),
    present INTEGER NOT NULL CHECK(present IN (0,1)),
    portions_prevues REAL NOT NULL CHECK(portions_prevues > 0),
    commentaire TEXT,
    UNIQUE(jour_repas,type_repas)
);
