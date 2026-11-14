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

**Question 1.** La chaîne du fragment propositionnel est complète : variables
booléennes et connecteurs `not`, `and`, `or` et `->` sont validés, compilés en
FNC par une transformation de Tseitin, sérialisés en DIMACS et résolus par le
DPLL de la partie I.

**Question 2.** La grammaire Lark (LALR) couvre le langage complet : `const`
(entiers et tableaux), `enum`, `var` et `array` sur `bool`, `a..b` ou un type
énuméré, boucles `forall` imbriquées, comparaisons, arithmétique (`+`, `-`,
`*`, moins unaire, `abs`), accès `grid[i][j]`, tranches `grid[i][*]` et
contraintes globales écrites comme des appels de fonction. Les quatre modèles
d'`exemples/` sont acceptés et transformés en AST.

Choix de la grammaire :

- les priorités sont encodées par niveaux, du plus faible au plus fort :
  `->`, `or`, `and`, `not`, comparaisons, `+ -`, `*`, moins unaire, atomes.
  `->` est associatif à droite, les autres opérateurs binaires à gauche ;
- une comparaison a deux opérandes arithmétiques : `a = b = c` est une erreur
  de syntaxe et `not x = 2` se lit `not (x = 2)` ;
- les onze mots-clés sont réservés ; `abs`, `allDifferent`, etc. sont de simples
  noms de fonctions ;
- après `[`, un `*` ne peut pas commencer une expression : c'est le joker d'une
  tranche, jamais une multiplication ;
- un nom dans un domaine (`var c : Color;`) ou une taille (`array a[Color]`)
  est distingué d'une expression par le symbole suivant, sans conflit LALR ;
- les boucles ne contiennent que des contraintes et des boucles.

Chaque nœud de l'AST conserve la ligne et la colonne où il commence dans le
texte. Ces positions n'interviennent pas dans l'égalité des nœuds. Les erreurs
sont signalées avec leur position, par exemple :

```text
modele.csp: ligne 2, colonne 17 : « ; » inattendu, attendu : un entier, un nom, « ( », « - » ou « not »
modele.csp: ligne 4, colonne 5 : nom non déclaré : w
```

L'analyseur ne vérifie que la forme du texte ; le sens est vérifié par la
question 3.

**Question 3.** Deux passes transforment l'AST en une liste de contraintes
sans boucle, qui ne portent plus que sur des cases de variables :

```text
AST --analyse()--> Model --expand()--> contraintes déroulées et simplifiées
```

- `analyse` (`semantics.py`) lit les déclarations dans l'ordre et construit la
  table des symboles : constantes évaluées, types énumérés et leurs valeurs,
  domaines et tailles de tableaux calculés. Elle vérifie ensuite le type de
  chaque contrainte dans la portée de ses boucles, sans les dérouler. Types :
  entier, booléen et un type par énumération. Une expression est *connue* si
  elle ne dépend que de littéraux, constantes, valeurs énumérées et indices de
  boucle ; tailles, bornes, indices et opérandes de l'arithmétique doivent
  l'être. Elle rejette : nom non déclaré ou déclaré deux fois (y compris un
  indice de boucle), types incompatibles, `<` sur des booléens, arithmétique
  sur une variable, valeur inconnue là où une valeur connue est exigée, mauvais
  nombre d'indices, type d'indice, tranche hors d'une contrainte globale,
  fonction inconnue ou mauvais arguments, domaine vide, taille de tableau
  invalide, tableau constant mal formé.
- `expand` (`expansion.py`) remplace chaque `forall` par ses instances
  (les bornes peuvent dépendre des indices précédents, `j in i..N`), calcule
  les valeurs connues, remplace les tranches par leurs cases (ligne par ligne)
  et simplifie les connecteurs dont un opérande est connu. Le calcul est
  paresseux : dans `i < N -> g[i + 1] != g[i]`, le membre droit n'est jamais
  évalué quand `i < N` est faux, donc `g[N + 1]` ne provoque pas d'erreur ; un
  accès hors bornes réellement évalué est une erreur. Les contraintes globales
  à arguments connus sont simplifiées (`atMostOne(x, y, vrai)` devient
  `not x and not y`).
- Normalisation des comparaisons, pour réduire les cas de la question 4 : une
  case comparée à une valeur est à gauche (`3 < x` devient `x > 3`), deux cases
  ne sont comparées qu'avec `=`, `!=`, `<`, `<=` (`x > y` devient `y < x`), et
  une comparaison niée est remplacée par la comparaison contraire
  (`not x = 2` devient `x != 2`).
- Une contrainte qui se simplifie en vrai disparaît. Une contrainte qui se
  simplifie en faux est conservée (le modèle est insatisfiable) et produit un
  avertissement sur la sortie d'erreur.

**Question 4.** `encoding.py` traduit les contraintes déroulées en formules
propositionnelles, puis `cnf.py` les met en FNC.

- *Encodage direct* : une variable de domaine `{v1, …, vk}` reçoit k variables
  SAT `x=v`, avec les clauses de `exactlyOne` (une clause « au moins une »,
  une clause binaire par paire). Une variable `bool` reste une seule variable
  SAT. Le fichier DIMACS nomme chacune (`c var 5 grid[1][2]=5`).
- *Comparaisons* (avec `x`, `y` de domaines `Dx`, `Dy`) :
  `x = v` est `x=v` ; `x != v` est `not x=v` ;
  `x < v` (et `<=`, `>`, `>=`) est soit « x prend une bonne valeur »
  (disjonction), soit « x ne prend aucune mauvaise valeur » (conjonction de
  négations) : grâce à `exactlyOne` les deux sont équivalentes, on garde la
  plus courte, et aucune ne demande d'auxiliaire au niveau supérieur ;
  `x = y` donne `x=v -> y=v` pour chaque `v` (|Dx| clauses binaires) ;
  `x != y` donne `not (x=v and y=v)` pour chaque valeur commune ;
  `x < y` donne, pour chaque `v` de `Dx`, la clause
  `x=v -> (y=w pour un w > v)`, sans auxiliaire ; de même pour `<=`.
- *Contraintes globales* : `atLeastOne` est une disjonction, `atMostOne`
  l'encodage deux à deux (n(n-1)/2 clauses), `exactlyOne` les deux ;
  `allDifferent` impose, pour chaque valeur, qu'au plus une expression la
  prenne.
- *Compteur séquentiel de Sinz* (`--amo sinz`) : `atMostOne` en 3n - 4 clauses
  et n - 1 auxiliaires. Ses clauses n'expriment « au plus un » que pour des
  auxiliaires bien choisies : elles ne définissent pas un littéral équivalent à
  `atMostOne`. On ne les utilise donc que là où la contrainte doit être vraie
  (domaines, contrainte entière), jamais sous une négation comme
  `b -> not atMostOne(...)`, où l'encodage deux à deux est employé.
- *Mise en FNC* (`cnf.py`) : les négations sont d'abord descendues jusqu'aux
  littéraux. Une conjonction donne les clauses de ses membres, une disjonction
  de littéraux est une clause : `a -> b` ou `not (a and b)` ne coûtent aucune
  auxiliaire. Ailleurs, une auxiliaire `t` est introduite pour une sous-formule
  `G` avec les seules clauses de `t -> G` (Tseitin dans une seule direction,
  suffisant puisque toutes les sous-formules apparaissent positivement).

Taille des FNC des modèles du sujet :

| Modèle | deux à deux | Sinz |
|---|---|---|
| pigeonhole.csp | 12 var. / 34 clauses | 29 var. / 48 clauses |
| queens.csp | 64 var. / 736 clauses | 176 var. / 608 clauses |
| coloring.csp | 30 var. / 87 clauses | 50 var. / 107 clauses |
| sudoku.csp | 729 var. / 11 775 clauses | 3 321 var. / 7 563 clauses |

Sinz réduit le nombre de clauses dès que les groupes `atMostOne` sont grands
(Sudoku : groupes de 9), au prix de nombreuses variables auxiliaires ; sur les
petits groupes (3 couleurs, 3 trous), il en ajoute.

**Question 5.** La jonction avec la partie I est complète. `dimacs.py` numérote
les variables propositionnelles et conserve leur nom dans des commentaires
`c var`, puis `csp.py` orchestre toute la chaîne :

```text
modèle CSP → FNC/DIMACS → DPLL de la partie I → valeurs du modèle CSP
```

- sans `--solve`, la CLI affiche la FNC ou l'écrit avec `--dimacs` ;
- avec `--solve`, elle appelle le solveur optimisé de la partie I
  (`question6.solver.dpll_optimized`), vérifie que sa valuation satisfait la
  FNC, puis décode uniquement les variables du modèle, jamais les auxiliaires ;
- les statuts attendus sont vérifiés sur les quatre exemples : pigeons UNSAT,
  reines SAT, coloration SAT et Sudoku SAT, avec les deux encodages
  `pairwise` et `sinz` ;
- pour les cas SAT, des oracles métier indépendants contrôlent les huit reines,
  la coloration du graphe de Petersen et toutes les règles du Sudoku.

La sortie contient `s SATISFIABLE` ou `s UNSATISFIABLE`, puis, dans le cas SAT,
une ligne `nom = valeur` par case, par exemple `grid[1][2] = 3` ou
`color[1] = Red`.

**Question 6 — en cours.** La question 6.1 est terminée. Le lecteur historique
de la partie I expose maintenant une `DescriptionGrille` contenant `N`, `M`,
l'ordre déclaré des zones et la matrice, tout en conservant l'ancienne fonction
`lire_grille`. `meowdoku.py` transforme cette description en préambule CSP :

```text
GRID/ZONES → const N, M, K → enum Zone → const region[N][M]
```

Le convertisseur conserve l'ordre de `ZONES`, refuse les noms qui ne peuvent
pas devenir des identifiants CSP et ne produit que les données propres à la
grille : les règles des deux modèles seront ajoutées ensuite. La grille 6 × 6 du
sujet est testée exactement ; la sortie est aussi relue par le parseur et
l'analyse sémantique. Les questions 6.2 à 6.6 (deux modèles complets,
vérificateur indépendant, mesures, contrainte redondante, généralisation et
conclusion expérimentale) ne sont pas encore implémentées.

- `syntax.py` contient la grammaire, les classes de l'AST, le parser,
  `pretty` (affichage de l'arbre) et `to_source` (réécriture de l'arbre dans le
  langage, entièrement parenthésée, telle que `parse(to_source(p)) == p`).
- `semantics.py` : table des symboles, vérification des types et évaluation
  des valeurs connues (question 3).
- `expansion.py` : déroulage, simplification et normalisation (question 3).
- `diagnostics.py` : l'exception `CompilationError` commune à toutes les passes.
- `encoding.py` : encodage direct, comparaisons, contraintes globales, Sinz et
  décodage du modèle (question 4).
- `cnf.py` : formules propositionnelles et mise en FNC (question 4).
- `compiler.py` : la chaîne de la question 1 (fragment propositionnel, Tseitin
  sur l'AST), conservée avec ses tests ; la CLI utilise désormais la chaîne
  complète.
- `dimacs.py` sérialise la FNC en conservant la correspondance des noms.
- `csp.py` orchestre la compilation, l'écriture DIMACS et la résolution.
- `tests/test_syntax.py` teste les priorités, associativités, erreurs de syntaxe
  et exemples du fragment.
- `tests/test_grammar.py` teste les constructions du langage complet, les
  nouvelles priorités, les erreurs de syntaxe et l'aller-retour
  texte → arbre → texte sur les quatre modèles du sujet.
- `tests/test_semantics.py` teste l'analyse (32 modèles erronés), le
  déroulage, le court-circuit, les simplifications, et vérifie par énumération
  que les contraintes déroulées ont exactement les mêmes solutions que le
  modèle source.
- `tests/test_encoding.py` teste la mise en FNC (équisatisfiabilité sur 300
  formules aléatoires), les clauses exactes des domaines et comparaisons, Sinz,
  et vérifie, pour chaque valeur possible des variables de petits modèles (un
  par opérateur de comparaison, plus des globales sous négation), que la FNC
  est satisfiable exactement quand le modèle source est vrai. Sur les exemples
  complets, il contrôle aussi directement les solutions décodées des reines,
  de la coloration du graphe de Petersen et du Sudoku avec des oracles métier
  indépendants du compilateur.
- `tests/test_compiler.py` teste la chaîne de la question 1 et la CLI.
- `meowdoku.py` convertit une grille `GRID/ZONES` de la partie I en
  déclarations CSP (`N`, `M`, `K`, `Zone` et `region`) pour la question 6.1.
- `tests/test_meowdoku.py` vérifie la conversion, les diagnostics, la CLI et
  l'acceptation du fichier produit par le compilateur CSP.
- `examples/` contient les petits exemples livrés avec le squelette.
- `exemples/` contient les quatre modèles complets du sujet : pigeons, reines,
  coloration du graphe de Petersen et Sudoku.
- `src/proplog/` est le paquet déclaré par le projet `uv` et sera développé au
  fil de la partie II.

## Environnement et commandes

Le `pyproject.toml` de cette partie déclare Python 3.13 et la dépendance Lark.
Le lockfile et le `.venv` sont partagés à la racine du dépôt. Depuis la racine :

```sh
uv sync
uv --directory partie_2 run python -m tests.test_syntax
uv --directory partie_2 run python -m unittest -v
uv --directory partie_2 run python csp.py examples/subject.csp
uv --directory partie_2 run python csp.py examples/subject.csp --solve
uv --directory partie_2 run python csp.py exemples/queens.csp --ast
uv --directory partie_2 run python csp.py exemples/queens.csp --expand
uv --directory partie_2 run python csp.py exemples/sudoku.csp --solve
uv --directory partie_2 run python csp.py exemples/sudoku.csp --solve --amo sinz
uv --directory partie_2 run python meowdoku.py \
  ../partie_1/grilles/grille.txt meowdoku-data.csp
```

La première commande `csp.py` affiche une FNC DIMACS. `--ast` affiche l'arbre
de syntaxe du modèle, sans le compiler. `--expand` affiche les contraintes
après déroulage et simplification, une par ligne. Avec `--solve`, le statut
SAT puis une valeur pour chaque variable du modèle sont affichés. Le fichier
`examples/syntax-error.csp` produit une erreur syntaxique expliquée, avec sa position.

La dernière commande ne génère que les données propres à la grille. Le fichier
`meowdoku-data.csp` peut ensuite être complété avec les règles de l'un des deux
modèles Meowdoku. L'ordre de la ligne `ZONES` devient l'ordre de l'énumération
`Zone` ; les noms incompatibles avec le langage CSP sont rejetés sans renommage.

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
