# Partie II — Un langage de contraintes compilé vers SAT

[← Retour à l'accueil](../README.md) · [Énoncé de la partie II](projet-part-2.pdf)

L'objectif est de construire un compilateur pour un petit langage de
contraintes. Il traduit un modèle en formule propositionnelle sous forme
normale conjonctive, appelle le solveur de la partie I, puis restitue les
valeurs des variables du modèle d'origine.

```text
texte .csp
  → AST Lark
  → analyse des noms et des types
  → expansion et simplification
  → encodage propositionnel
  → FNC / DIMACS
  → solveur DPLL de la partie I
  → modèle dans les termes du fichier .csp
```

## État actuel

La chaîne du fragment propositionnel est complète : variables booléennes et
connecteurs `not`, `and`, `or` et `->` sont validés, compilés en FNC par une
transformation de Tseitin, sérialisés en DIMACS et résolus par le DPLL de la
partie I.

- `syntax.py` contient la grammaire Lark LALR, les classes de l'AST, le parser
  et le pretty-printer.
- `compiler.py` valide les noms et réalise l'encodage de Tseitin.
- `dimacs.py` sérialise la FNC en conservant la correspondance des noms.
- `csp.py` orchestre la compilation, l'écriture DIMACS et la résolution.
- `tests/test_syntax.py` teste les priorités, associativités, erreurs de syntaxe
  et exemples du fragment.
- `examples/` contient les petits exemples livrés avec le squelette.
- `exemples/` contient les quatre modèles complets du sujet : pigeons, reines,
  coloration du graphe de Petersen et Sudoku.
- `src/proplog/` est le paquet déclaré par le projet `uv` et sera développé au
  fil de la partie II.

Les quatre modèles complets ne sont pas encore acceptés : ils nécessitent les
constantes, domaines finis, tableaux, boucles et contraintes globales des
questions suivantes.

## Environnement et commandes

Le `pyproject.toml` de cette partie déclare Python 3.13 et la dépendance Lark.
Le lockfile et le `.venv` sont partagés à la racine du dépôt. Depuis la racine :

```sh
uv sync
uv --directory partie_2 run python -m tests.test_syntax
uv --directory partie_2 run python -m unittest -v
uv --directory partie_2 run python csp.py examples/subject.csp
uv --directory partie_2 run python csp.py examples/subject.csp --solve
```

La première commande `csp.py` affiche une FNC DIMACS. Avec `--solve`, le statut
SAT puis une valeur pour chaque variable du modèle sont affichés. Le fichier
`examples/syntax-error.csp` produit une erreur syntaxique avec sa position.

Une sortie peut aussi être écrite dans un fichier, avec ou sans résolution :

```sh
uv --directory partie_2 run python csp.py examples/subject.csp --dimacs subject.cnf
uv --directory partie_2 run python csp.py examples/subject.csp --dimacs subject.cnf --solve
```

## Fragment propositionnel

Exemple accepté actuellement :

```text
var x : bool;
var y : bool;
var z : bool;

constraint x or y;
constraint (not x) and z;
constraint z -> y;
```

Les connecteurs sont, du plus prioritaire au moins prioritaire, `not`, `and`,
`or`, puis `->`. `and` et `or` sont associatifs à gauche ; `->` est associatif à
droite. Les mots-clés sont réservés.

La compilation rejette les déclarations doubles et toute référence à une
variable non déclarée avec un diagnostic contrôlé.
