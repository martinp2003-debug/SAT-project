# Question 4 — Heuristiques de branchement pour DPLL

Le programme `question4/heuristiques.py` implémente l'algorithme DPLL\(_H\) :
la propagation unitaire et l'élimination des littéraux purs restent prioritaires,
mais le choix de branchement est confié à une heuristique. Comme l'algorithme 2,
il renvoie un statut SAT/UNSAT et une valuation lorsque la formule est
satisfiable.

## Heuristiques retenues

Cinq choix sont disponibles :

- **H0 — CA** : choix aléatoire de la variable et de sa valeur. Cette version
  reproduit la référence de la question 2 et permet une comparaison ultérieure.
- **H1 — PVL** : plus petit identifiant de variable encore présent, essayé à
  vrai. Ce choix est déterministe, peu coûteux et joue le rôle d'ordre statique.
- **H3 — LP dynamique** : littéral ayant le plus d'occurrences dans la formule
  courante. Il choisit directement une polarité et satisfait potentiellement un
  grand nombre de clauses.
- **H4 — VFCM dynamique** : variable la plus fréquente dans les clauses de
  taille minimale, avec leur polarité majoritaire. Les petites clauses sont
  privilégiées car elles risquent davantage de devenir unitaires ou vides.
- **H7 — LJW dynamique** : littéral maximisant
  \(\sum_k \#_k(l,F)2^{-k}\). La pondération de Jeroslow–Wang tient compte de
  toutes les clauses tout en donnant plus d'importance aux plus petites.

Ces choix satisfont les contraintes de l'énoncé : H3 et H7 choisissent un
littéral, H4 et H7 exploitent la taille des clauses, et H3, H4 et H7 sont
dynamiques. Leur score est recalculé après les simplifications à chaque nœud de
branchement. En cas d'égalité, le plus petit identifiant est choisi, puis la
polarité positive, afin de rendre les essais reproductibles.

## Validation

Chaque heuristique est comparée à un oracle exhaustif sur les 512 formules
possibles construites avec les clauses non tautologiques sur deux variables,
puis sur 100 formules pseudo-aléatoires de la question 2. Les tests couvrent
également les 11 instances publiques d'interface et de cas limites, la formule
Meowdoku, la conservation de la formule d'entrée et la validité des valuations.

Cette question porte sur la correction et le choix des heuristiques. Leur
instrumentation et la comparaison de leurs performances relèvent de la
question 5.

## Utilisation

```sh
python3 question4/heuristiques.py instances/grille.cnf --heuristique h7 --output-model
python3 -m unittest -v question4.test_heuristiques
```
