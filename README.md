# Projet MLSF — Meowdoku et compilation vers SAT

Ce dépôt rassemble les deux parties du projet de Modélisation Logique et
Satisfaction de Contraintes. La première construit un solveur SAT autour de
DPLL et l'applique au Meowdoku. La seconde construit un langage de contraintes
compilé vers SAT et réutilisera ce solveur.

## Organisation

| Partie | Contenu | Documentation | Énoncé |
|---|---|---|---|
| I | Modélisation du Meowdoku, DPLL optimisé, heuristiques et mesures | [`partie_1/README.md`](partie_1/README.md) | [`MLSF_26_27_Projet.pdf`](partie_1/MLSF_26_27_Projet.pdf) |
| II | Langage de contraintes, compilation en FNC et jonction avec DPLL | [`partie_2/README.md`](partie_2/README.md) | [`projet-part-2.pdf`](partie_2/projet-part-2.pdf) |

```text
.
├── partie_1/   # solveur SAT et Meowdoku
├── partie_2/   # compilateur du langage de contraintes
├── pyproject.toml
└── uv.lock
```

La partie II dépend conceptuellement du solveur de la partie I. Cette jonction
sera réalisée derrière un adaptateur explicite ; les deux parties restent pour
l'instant exécutables et testables séparément.

## Environnement partagé

Le dépôt utilise Python 3.13 et un workspace `uv`. Une seule commande crée le
`.venv` commun à la racine et installe les dépendances de la partie II :

```sh
uv sync
```

Les commandes suivantes sont à lancer depuis la racine :

```sh
# Partie I : suite complète
uv --directory partie_1 run python -m unittest -v

# Partie I : interface finale et solveur optimisé
uv --directory partie_1 run python sat.py instances/grille.cnf --output-model

# Partie II : tests du fragment propositionnel
uv --directory partie_2 run python -m tests.test_syntax

# Partie II : analyse d'un exemple
uv --directory partie_2 run python csp.py examples/subject.csp
```

`uv --directory` change le répertoire de travail de la commande tout en
réutilisant le workspace, son lockfile et le `.venv` situés à la racine.
