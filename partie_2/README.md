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

Le code de départ traite uniquement le fragment propositionnel : variables
booléennes et connecteurs `not`, `and`, `or` et `->`.

- `syntax.py` contient la grammaire Lark LALR, les classes de l'AST, le parser
  et le pretty-printer.
- `csp.py` fournit la ligne de commande qui analyse un modèle et affiche son
  AST.
- `tests/test_syntax.py` teste les priorités, associativités, erreurs de syntaxe
  et exemples du fragment.
- `examples/` contient les petits exemples livrés avec le squelette.
- `exemples/` contient les quatre modèles complets du sujet : pigeons, reines,
  coloration du graphe de Petersen et Sudoku.
- `src/proplog/` est le paquet déclaré par le projet `uv` et sera développé au
  fil de la partie II.

Les quatre modèles complets ne sont pas encore acceptés : étendre le langage et
fermer la chaîne jusqu'au solveur constitue précisément le travail demandé.

## Environnement et commandes

Le `pyproject.toml` de cette partie déclare Python 3.13 et la dépendance Lark.
Le lockfile et le `.venv` sont partagés à la racine du dépôt. Depuis la racine :

```sh
uv sync
uv --directory partie_2 run python -m tests.test_syntax
uv --directory partie_2 run python csp.py examples/subject.csp
```

La dernière commande doit afficher un AST commençant par `Program`. Le fichier
`examples/syntax-error.csp` doit au contraire produire une erreur syntaxique
avec sa position.

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

Le parser ne vérifie pas encore la déclaration des noms : par exemple,
`constraint w;` est syntaxiquement valide. Cette vérification appartient à la
première étape de l'analyse sémantique.
