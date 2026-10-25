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

Deux campagnes ont été réalisées le 25 octobre 2026. La première utilise
Python 3.11.5 directement sous macOS 26.6.2 ARM64. La seconde utilise l'image
Docker `python:3.12-slim` en architecture `linux/amd64`, avec les limites du
sujet : 4 CPU et 8 Gio de mémoire. Le projet y est monté en lecture seule et le
réseau est désactivé. Cette seconde campagne reproduit donc l'image, la version
majeure de Python, l'architecture et les limites de ressources de la
compétition. Le processeur x86-64 reste toutefois émulé sur l'Apple M1 et ne
reproduit pas les performances de l'Intel Core Ultra 7 155H cible.

## Résultats sous Docker

| Solveur | Correctes | SAT | UNSAT | Timeouts | Temps des instances correctes (s) |
|---|---:|---:|---:|---:|---:|
| DPLL Q2 | 51/55 | 27 | 24 | 4 | 65,708 |
| Optimisé H1 | 53/55 | 29 | 24 | 2 | **46,434** |
| Optimisé H4 | **54/55** | **30** | 24 | **1** | 105,204 |
| Optimisé adaptatif | **54/55** | **30** | 24 | **1** | 103,240 |

Sur les 51 instances résolues par les quatre variantes, le temps cumulé passe
de 65,708 s pour DPLL à 78,239 s pour l'adaptatif et 32,799 s pour H1. Ce
résultat agrégé ne signifie pas que H1 donne le meilleur classement : il ne
résout que 53 instances, contre 54 pour H4 et l'adaptatif, et le nombre
d'instances correctes est le premier critère du sujet. Le coût fixe d'environ
0,33 s observé sur les cas les plus faciles est inclus ; il provient en grande
partie du lancement d'un processus Python x86-64 sous émulation.

### Détail par famille

| Famille | DPLL Q2 | H1 | H4 | Adaptatif |
|---|---:|---:|---:|---:|
| Publiques | 26/30 | 28/30 | **29/30** | **29/30** |
| Meowdoku | 25/25 | 25/25 | 25/25 | 25/25 |

Le DPLL initial dépasse 60 s sur `public-03`, `public-06`, `public-12` et
`public-27`. L'adaptatif résout les trois dernières et ne dépasse la limite que
sur `public-03`, instance UNSAT. Aucune réponse incorrecte ni aucun modèle
invalide n'a été observé : toutes les instances non résolues sont des timeouts.

La campagne native macOS aboutit exactement aux mêmes nombres d'instances
correctes et de timeouts. Ses temps cumulés respectifs sont 34,251 s, 15,755 s,
40,906 s et 39,379 s. Les deux environnements confirment donc les conclusions
fonctionnelles et le classement par couverture, mais leurs temps absolus ne
doivent pas être comparés directement.

## Fonctionnement et analyse du choix adaptatif

Après le prétraitement, le solveur examine une fois la structure de la formule.
Il la considère de type Meowdoku si elle contient au moins une clause entièrement
positive et si au moins 70 % de ses clauses non vides sont des clauses binaires
entièrement négatives. Cette forme est caractéristique de l'encodage : les
clauses positives imposent la présence d'un chat, tandis que les nombreuses
clauses `(¬x ∨ ¬y)` interdisent des paires de positions.

Si le test réussit, la stratégie H1 est conservée pendant toute la recherche :
elle choisit la plus petite variable encore libre et essaie d'abord la valeur
vraie. Sinon, le solveur conserve H4/MOMS : à chaque décision, il considère les
clauses non satisfaites, ne garde que les plus courtes, choisit la variable qui
y apparaît le plus souvent et essaie sa polarité majoritaire. Le terme
`adaptatif` désigne donc ici une sélection automatique au niveau de l'instance,
et non un changement entre H1 et H4 pendant l'exploration. H4 reste, elle,
dynamique puisque ses fréquences sont recalculées sur l'état courant.

Le détecteur sélectionne H1 pour les 25 instances Meowdoku. Ce choix est
cohérent avec la question 5 et réduit, sous Docker, leur temps cumulé de
23,273 s avec DPLL à 10,573 s. H4 demande 14,925 s sur ce même lot.

Sur les instances publiques, H4 est nécessaire pour résoudre `public-12` en
16,7 s sous Docker, alors que H1 dépasse 60 s. H1 est néanmoins beaucoup plus
rapide sur quelques instances SAT, notamment `public-04` : 0,68 s contre
53,67 s pour l'adaptatif. Aucune stratégie ne domine donc sur chaque instance.
Selon le classement du sujet, H1 seul reste derrière car ses 53 instances
résolues priment sur son meilleur temps total. H4 et l'adaptatif résolvent tous
deux 54 instances ; l'adaptatif est retenu car son temps total est plus faible
sur l'ensemble et qu'il est spécialement adapté aux Meowdoku.

## Limites

- Les variantes déterministes n'ont été exécutées qu'une fois : les petits
  temps restent sensibles au bruit du système.
- Le DPLL aléatoire n'est mesuré qu'avec la graine 0 afin de rendre la comparaison
  reproductible ; une autre graine peut modifier fortement ses performances.
- Les temps Docker subissent le coût de l'émulation x86-64 sur Apple M1 et ne
  sont pas directement comparables à ceux de la machine de compétition. Les
  statuts, modèles et nombres d'instances résolues restent vérifiables.
- Les résultats bruts natifs et Docker sont conservés respectivement dans
  `question6/resultats_q6.csv` et `question6/resultats_q6_docker.csv`.

## Reproduction

```sh
python3 -m unittest discover -v
python3 question6/benchmark_q6.py mesurer --limite 60 > question6/resultats_q6.csv
python3 question6/benchmark_q6.py resumer question6/resultats_q6.csv
docker compose run --rm solver python question6/benchmark_q6.py mesurer \
  --limite 60 > question6/resultats_q6_docker.csv
docker compose run --rm solver python question6/benchmark_q6.py resumer \
  question6/resultats_q6_docker.csv
```
