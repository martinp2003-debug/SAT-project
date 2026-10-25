# Question 6 — Validation et évaluation du solveur optimisé

## Validation

Le mode `optimized` a été validé indépendamment de ses performances :

- les 37 tests du projet réussissent ;
- les 512 formules possibles construites avec les 9 clauses sans tautologie
  sur deux variables sont comparées à une énumération exhaustive ;
- 500 formules pseudo-aléatoires de 1 à 6 variables sont résolues avec H1, H4
  et la sélection adaptative, puis comparées au même oracle ;
- le prétraitement est testé sans modification de la formule d'entrée ;
- le trail est contrôlé après des conflits dans les deux branches : les
  affectations du niveau sont annulées et les affectations racines conservées ;
- l'interface sans option, les deux modes, les sorties SAT/UNSAT et le format
  du modèle sont testés ;
- chaque modèle des benchmarks est relu puis vérifié clause par clause avec
  `question2.sat.verifier_valuation`.

La compilation de tous les modules avec `compileall` réussit et chaque nouvelle
fonction possède des annotations. Aucun vérificateur statique comme mypy ou
Pyright n'était installé dans l'environnement de mesure.

## Protocole d'évaluation

Le benchmark lance le véritable point d'entrée `sat.py` dans un sous-processus.
Le temps mural comprend donc le démarrage de Python, la lecture DIMACS, la
résolution et la production du modèle. Chaque exécution est limitée à 60 s.
La sortie standard, l'absence de sortie d'erreur, le statut et les modèles SAT
sont contrôlés indépendamment.

Le lot contient 55 instances : 30 instances publiques et 25 Meowdoku de la
question 5, soit 30 SAT et 25 UNSAT. Quatre variantes sont comparées :

- `dpll` : algorithme de la question 2, avec la graine 0 ;
- `optimized-h1` : moteur incrémental et H1 imposée ;
- `optimized-h4` : moteur incrémental et H4/MOMS imposée ;
- `optimized-adaptive` : H1 pour les formules dominées par les clauses binaires
  négatives, H4 sinon.

Mesures réalisées le 25 octobre 2026 sous Python 3.11.5, macOS 26.6.2 ARM64.
Docker était installé mais son daemon n'était pas actif : l'environnement cible
Python 3.12/Linux du sujet n'a donc pas pu être reproduit localement.

## Résultats

| Solveur | Correctes | SAT | UNSAT | Timeouts | Temps des instances correctes (s) |
|---|---:|---:|---:|---:|---:|
| DPLL Q2 | 51/55 | 27 | 24 | 4 | 34,251 |
| Optimisé H1 | 53/55 | 29 | 24 | 2 | **15,755** |
| Optimisé H4 | **54/55** | **30** | 24 | **1** | 40,906 |
| Optimisé adaptatif | **54/55** | **30** | 24 | **1** | 39,379 |

Sur les 51 instances résolues par les quatre variantes, le temps cumulé passe
de 34,251 s pour DPLL à 27,854 s pour l'adaptatif. Le coût fixe du lancement de
Python, environ 0,04 s sur les cas les plus faciles, est inclus.

### Détail par famille

| Famille | DPLL Q2 | H1 | H4 | Adaptatif |
|---|---:|---:|---:|---:|
| Publiques | 26/30 | 28/30 | **29/30** | **29/30** |
| Meowdoku | 25/25 | 25/25 | 25/25 | 25/25 |

Le DPLL initial dépasse 60 s sur `public-03`, `public-06`, `public-12` et
`public-27`. L'adaptatif résout les trois dernières et ne dépasse la limite que
sur `public-03`, instance UNSAT. Aucune réponse incorrecte ni aucun modèle
invalide n'a été observé : toutes les instances non résolues sont des timeouts.

## Analyse du choix adaptatif

Le détecteur sélectionne H1 pour les 25 instances Meowdoku. Ce choix est
cohérent avec la question 5 et réduit leur temps cumulé de 9,963 s avec DPLL à
2,118 s. H4 demande 4,187 s sur ce même lot.

Sur les instances publiques, H4 est nécessaire pour résoudre `public-12` en
7,9 s, alors que H1 dépasse 60 s. H1 est néanmoins beaucoup plus rapide sur
quelques instances SAT, par exemple `public-04`. Aucune stratégie ne domine donc
sur chaque instance. Selon le classement du sujet, H1 seul reste derrière car
ses 53 instances résolues priment sur son meilleur temps total. H4 et
l'adaptatif résolvent tous deux 54 instances ; l'adaptatif est retenu, car il
est plus rapide sur l'ensemble et spécialement adapté aux Meowdoku.

## Limites

- Les variantes déterministes n'ont été exécutées qu'une fois : les petits
  temps restent sensibles au bruit du système.
- Le DPLL aléatoire n'est mesuré qu'avec la graine 0 afin de rendre la comparaison
  reproductible ; une autre graine peut modifier fortement ses performances.
- Les temps locaux ne sont pas directement comparables à ceux de la machine de
  compétition, mais les statuts, modèles et nombres d'instances résolues restent
  vérifiables.
- Les résultats bruts sont conservés dans `question6/resultats_q6.csv`.

## Reproduction

```sh
python3 -m unittest discover -v
python3 question6/benchmark_q6.py mesurer --limite 60 > question6/resultats_q6.csv
python3 question6/benchmark_q6.py resumer question6/resultats_q6.csv
```
