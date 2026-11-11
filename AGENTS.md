# AGENTS.md

## Mission

Ce dépôt contient le projet de Modélisation Logique et Satisfaction de
Contraintes : construire en Python un compilateur d'un petit langage de
contraintes vers SAT, puis résoudre les formules produites avec le solveur DPLL
de la partie I.

Le travail doit rester pédagogique : avant une modification importante,
expliquer brièvement l'architecture, le flux de données et le compromis retenu.
Préférer une implémentation plus petite, testée et comprise à une couverture
fragile de tout le langage.

L'énoncé de référence de la partie II est `projet-part-2.pdf`. En cas
d'ambiguïté, l'énoncé prime sur ce fichier, puis les décisions explicitement
prises avec l'utilisateur priment sur les recommandations générales.

## État initial du dépôt

- `question1/` à `question5/` : travail de la partie I.
- `question2/sat.py` : lecture DIMACS, DPLL et DPLL avec valuation à réutiliser.
- `question4/heuristiques.py` : DPLL avec heuristiques de branchement.
- `question5/instrumentation.py` : solveur instrumenté pour les expériences.
- `proplog/` : code de départ de la partie II, limité au fragment propositionnel.
- `proplog/syntax.py` : grammaire Lark LALR, AST et pretty-printer actuels.
- `proplog/csp.py` : interface en ligne de commande actuelle.
- `proplog/tests/` : tests du fragment propositionnel.
- `exemples/` : quatre modèles complets servant de tests d'acceptation.
- `grilles/`, `instances/`, `public-instances/` : données de la partie I.

Ne pas réécrire le solveur SAT dans `proplog`. La partie II doit appeler le
solveur existant derrière une frontière claire, afin que compilation et
résolution restent testables séparément.

## Architecture cible

Conserver une chaîne de compilation explicite, composée de passes :

```text
texte .csp
  -> analyse lexicale et syntaxique Lark
  -> AST de surface
  -> analyse des noms et des types
  -> expansion des forall, tranches et valeurs connues
  -> contraintes normalisées sans boucle
  -> encodage des domaines finis en variables propositionnelles
  -> formule propositionnelle
  -> FNC et numérotation DIMACS
  -> solveur DPLL de la partie I
  -> décodage du modèle vers les variables du fichier .csp
```

Chaque passe doit avoir un contrat simple, des entrées/sorties inspectables et
des tests ciblés. Ne pas construire une fonction monolithique qui parse,
transforme, encode et résout en un seul parcours.

Découpage conceptuel recommandé, à adapter aux conventions qui émergeront :

- syntaxe : grammaire, nœuds de l'AST, parsing et pretty-printing ;
- sémantique : table des symboles, résolution des noms, types et diagnostics ;
- expansion : `forall`, calcul des valeurs connues, court-circuit et tranches ;
- encodage : domaines, comparaisons, contraintes globales et Tseitin ;
- DIMACS : numérotation, sérialisation et correspondance noms/variables ;
- exécution : appel du solveur et décodage de sa valuation ;
- CLI : orchestration uniquement, sans logique métier majeure.

Ne créer de nouveaux modules que lorsqu'une responsabilité testable le
justifie. Éviter les abstractions anticipées et les dépendances autres que Lark
sans besoin démontré.

## Contrats du langage à préserver

### Syntaxe

- Le parseur doit rester LALR(1) avec `parser="lalr"`.
- Les priorités et associativités sont encodées dans la grammaire, pas réparées
  après parsing.
- Les mots réservés de l'énoncé ne peuvent pas devenir des identifiants.
- Les comparaisons ne s'enchaînent pas : `a = b = c` est invalide.
- Une tranche avec `*` n'est admise qu'en argument d'une contrainte globale.
- Les quatre fichiers de `exemples/` doivent finir par être acceptés.

### Noms, types et domaines

- Constantes, types, valeurs d'énumération, variables, tableaux et indices de
  boucle partagent un même espace de noms.
- Les tableaux du langage sont indexés à partir de 1. Un tableau indexé par une
  énumération suit l'ordre de déclaration de ses valeurs.
- Les opérations arithmétiques ne portent que sur des valeurs connues à la
  compilation. Une expression telle que `x + 1` est invalide si `x` est une
  variable du problème.
- Les comparaisons ordonnées portent sur des entiers ou des valeurs d'un même
  type énuméré. Sur les booléens, seules `=` et `!=` sont admises.
- Tout nom inconnu, doublon, type incompatible, mauvais nombre d'indices ou
  argument invalide doit produire un diagnostic contrôlé, jamais une trace
  Python brute destinée à l'utilisateur.

### Valeurs connues et court-circuit

Une valeur est connue si elle dépend uniquement de littéraux, constantes,
valeurs d'énumération, indices de boucle ou cases de tableaux constants.

Le calcul doit respecter le court-circuit. Exemple :

```text
constraint i < N -> grid[i + 1][1] != grid[i][1];
```

Pour `i = N`, le membre droit ne doit pas être évalué : l'accès `grid[N+1]`
est protégé par une prémisse connue fausse. En revanche, tout accès hors bornes
effectivement évalué est une erreur de compilation. Cet invariant doit avoir
des tests positifs et négatifs dédiés.

### Encodage SAT

- Une variable de domaine fini utilise par défaut l'encodage direct : un
  booléen SAT par valeur, avec exactement une valeur vraie.
- Une variable `bool` reste une seule variable propositionnelle.
- Les valeurs d'une énumération sont ordonnées selon leur déclaration.
- `atMostOne` utilise d'abord l'encodage deux à deux demandé par l'énoncé.
- `atLeastOne`, `atMostOne`, `exactlyOne` et `allDifferent` doivent être
  testables indépendamment de la CLI.
- La transformation de Tseitin doit préserver la satisfiabilité et permettre
  de retrouver la valuation des variables nommées. Les variables auxiliaires
  ne sont pas affichées à l'utilisateur.
- Garder une correspondance bidirectionnelle stable entre objets du modèle et
  identifiants DIMACS ; ne pas déduire les noms après coup depuis des chaînes.

## Interface attendue

Viser l'interface conseillée par l'énoncé, sauf décision contraire documentée :

```sh
python csp.py model.csp
python csp.py model.csp --dimacs formule.cnf
python csp.py model.csp --solve
```

Sans `--solve`, la sortie est une FNC DIMACS. Avec `--solve`, afficher
`s SATISFIABLE` ou `s UNSATISFIABLE`, puis une ligne `nom = valeur` par
variable du modèle lorsque celui-ci est satisfiable.

La CLI traduit les erreurs attendues en messages lisibles sur stderr et en code
de sortie non nul. Quand les métadonnées Lark sont disponibles, inclure le
fichier, la ligne et la colonne.

## Tests et critères d'acceptation

Tester chaque passe à son niveau, puis la chaîne complète. Couvrir au minimum :

- priorités, associativités, mots réservés et erreurs de syntaxe ;
- symboles dupliqués ou inconnus, types incompatibles et indices invalides ;
- expansion de petites boucles, tranches et court-circuit ;
- encodages de domaines, comparaisons et contraintes globales ;
- équivalence de satisfiabilité entre une petite formule source et sa FNC ;
- décodage d'une valuation SAT vers les valeurs du modèle ;
- erreurs de lecture ou de compilation via la CLI.

Tests d'acceptation finaux :

| Modèle | Résultat attendu |
|---|---|
| `exemples/pigeonhole.csp` | UNSAT |
| `exemples/queens.csp` | SAT |
| `exemples/coloring.csp` | SAT |
| `exemples/sudoku.csp` | SAT |

Pour un résultat SAT, vérifier aussi la solution métier ; le seul statut SAT ne
suffit pas. Pour les transformations délicates, ajouter de petits tests
exhaustifs avant de lancer les gros exemples.

Commandes de référence actuelles :

```sh
# Partie I, depuis la racine
python3 -m unittest -v

# Fragment propositionnel initial, depuis proplog/
uv sync
uv run python -m tests.test_syntax
```

Adapter ces commandes si l'organisation du paquet change, puis mettre à jour
ce fichier et le `README.md` dans la même modification.

## Ordre de réalisation

Avancer verticalement plutôt que d'étendre toutes les couches séparément :

1. fermer la chaîne complète pour le fragment propositionnel ;
2. étendre la grammaire et l'AST avec des tests de parsing ;
3. ajouter analyse sémantique, valeurs connues et expansion ;
4. encoder domaines finis, comparaisons et contraintes globales ;
5. raccorder DIMACS, solveur et décodage ;
6. modéliser Meowdoku et mener les expériences comparatives.

Lors d'une étape, privilégier d'abord un petit sous-ensemble traversant toutes
les passes, par exemple variables entières et égalité sans `forall`, puis
élargir sans casser les tests précédents.

## Méthode de travail pour les agents

Avant de proposer une modification :

1. lire les fichiers concernés, leurs tests et les sections pertinentes de
   l'énoncé ;
2. vérifier les conventions existantes et l'état Git sans modifier les travaux
   non liés ;
3. pour une décision structurante, présenter le flux de données, le choix
   recommandé, ses limites et attendre l'accord de l'utilisateur ;
4. après accord, implémenter et tester de façon autonome les détails courants ;
5. signaler tout écart architectural important avant de poursuivre.

Après une modification :

- exécuter les tests ciblés puis les tests de non-régression pertinents ;
- distinguer clairement ce qui a été exécuté de ce qui reste à vérifier ;
- donner un test manuel court avec commande et résultat attendu ;
- expliquer les contrats ou invariants importants plutôt que chaque ligne ;
- mettre à jour la documentation si une commande, une interface ou une
  décision stable a changé.

Ne pas relire ou résumer l'intégralité du PDF pour une question locale : partir
de cette carte, puis consulter seulement la section de l'énoncé et les fichiers
directement concernés.

## Non-objectifs initiaux

Sauf demande explicite, ne pas commencer par les extensions optionnelles :
`<->`, compréhensions, `count`, `sum`, encodage par ordre ou compteur de Sinz.
Ne pas optimiser le solveur de la partie I pour masquer une mauvaise
modélisation. Mesurer avant d'optimiser et conserver une version correcte de
référence.
