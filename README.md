# Meowdoku — Questions 1 à 5

Ces programmes utilisent uniquement la bibliothèque standard de Python 3.

## Fichiers

- `question1/conversion.py` : lecture et validation d'une grille, puis conversion en CNF.
- `question1/generation.py` : génération d'une grille possédant au moins une solution.
- `grilles/grille.txt` : grille d'exemple de la figure 1 du sujet.
- `instances/grille.cnf` : conversion de cette grille au format DIMACS.
- `question2/sat.py` : lecteur DIMACS et les deux versions de DPLL (question 2).
- `question2/test_sat.py` : validation du lecteur, des solveurs et de la commande.
- `question2/benchmark_q2.py` : comparaison des temps CPU des deux versions.
- `question2/resultats_q2.csv` : résultats des mesures de performances.
- `question2/rapport_q2.md` : choix de conception, validation et analyse des performances.
- `question3/solution.py` : recherche, validation et affichage d'une solution.
- `question3/test_solution.py` : tests de la chaîne complète de résolution.
- `question3/solution_grille.txt` : résultat obtenu pour la grille du sujet.
- `question3/rapport_q3.md` : conception et validation de la question 3.
- `question4/heuristiques.py` : DPLL avec cinq heuristiques de branchement.
- `question4/test_heuristiques.py` : validation des heuristiques et valuations.
- `question4/rapport_q4.md` : justification des choix de la question 4.
- `question5/instrumentation.py` : DPLL_H instrumenté (compteurs, temps, délai) et variantes statiques.
- `question5/instances_meowdoku.py` : génération d'instances Meowdoku SAT et UNSAT.
- `question5/benchmark_q5.py` : campagne de mesures et tableaux de synthèse.
- `question5/resultats_q5.csv` : mesures brutes de la question 5.
- `question5/rapport_q5.md` : protocole, résultats et analyse des performances.
- `grilles/q5/`, `instances/q5/` : grilles et CNF générées pour la question 5.
- `public-instances/` : tests et instances de performance fournis par les enseignants.

## Utilisation

Depuis le dossier du projet :

```sh
python3 question1/conversion.py grilles/grille.txt instances/grille.cnf
python3 question1/generation.py 6 grilles/generee.txt --seed 42
python3 question1/conversion.py grilles/generee.txt instances/generee.cnf
```

Les fichiers de sortie existants sont remplacés. Les dossiers de sortie sont
créés si nécessaire. L'option `--seed` est facultative.

## Modélisation

La variable `x[i,j]` signifie qu'un chat occupe la case `(i,j)`. Les régions sont
des données fixes de la grille. Avec des indices Python commençant à 0,
l'identifiant DIMACS de cette variable est `i*M+j+1`.

- Ligne et colonne : clause `[-a, -b]` pour chaque paire de cases distinctes.
- Région : une clause contenant toutes ses variables positives (au moins un
  chat), puis `[-a, -b]` pour chaque paire (au plus un chat).
- Voisinage : les contacts horizontaux et verticaux sont déjà interdits par les
  lignes et colonnes. On ajoute donc les deux diagonales descendantes, avec le
  contrôle `0 <= ni < N and 0 <= nj < M` avant de créer une clause.

La conversion accepte les grilles rectangulaires et ne suppose pas `N = M = K`.
Certaines clauses peuvent apparaître plusieurs fois lorsqu'une paire partage
plusieurs contraintes ; cela ne change pas la satisfiabilité.

## Construction des grilles

Le générateur se restreint à `N = M = K`, comme autorisé dans le sujet.
On essaie les colonnes de départ entre `0` et `N-1` dans un ordre aléatoire,
sans répétition. Depuis chaque départ, on avance de 2 en 2, puis on parcourt
l'autre parité depuis son plus petit indice, puis les colonnes restantes de
la parité initiale dans l'ordre croissant. Par exemple, pour `N = 6` et un
départ en colonne `3`, on obtient `[3, 5, 0, 2, 4, 1]`.
Chaque colonne est utilisée une seule fois, avec un chat par ligne.
On accepte le placement seulement si deux colonnes consécutives diffèrent
d'au moins 2, pour éviter tout contact diagonal, y compris aux raccords.
Sinon, on essaie le départ suivant. Pour `N >= 4`, le départ `1` fonctionne
toujours : la recherche termine donc après au plus `N` essais. Le départ
final est aléatoire parmi ceux qui donnent un parcours valide avec cette règle.

Chaque chat initialise ensuite sa propre région. Les régions s'étendent
aléatoirement aux cases libres voisines horizontalement ou verticalement jusqu'à
remplir la grille. Elles restent connexes, disjointes, et contiennent chacune
exactement un chat du placement initial. Celui-ci constitue donc une solution.
Cette construction garantit l'existence d'une solution, sans garantir son unicité
ni une difficulté particulière.

La taille 1 est acceptée. Les tailles 2 et 3 sont impossibles dans le cas
`N = M = K` et sont rejetées explicitement.

## Question 2 — Résolution SAT

```sh
# Algorithme 1 : statut uniquement.
python3 question2/sat.py instances/grille.cnf --version 1 --seed 0

# Algorithme 2 (par défaut) : statut et, sur demande, valuation.
python3 question2/sat.py instances/grille.cnf --mode dpll --output-model --seed 0

# Validation et mesures reproductibles sur deux instances publiques.
python3 -m unittest -v
python3 question2/benchmark_q2.py public-instances --repetitions 100 --limite 2

# Lot public complet : potentiellement très long avec le DPLL de base.
python3 question2/benchmark_q2.py public-instances --repetitions 1
```

Le résultat de `grille.cnf` est `s SATISFIABLE`. Avec `--output-model`, une ligne
`v ... 0` donne une valuation complète, vérifiée contre les clauses initiales.
`--stats` affiche le temps CPU du solveur sur stderr, sans modifier le format
de stdout. `--seed` rend les décisions aléatoires reproductibles.
`--version 1 --output-model` est rejeté car l'algorithme 1 ne calcule pas de modèle.

En Python, `lire_dimacs(chemin)` renvoie `(nombre_variables, formule)`,
`dpll(formule, seed=None)` renvoie un booléen et
`dpll_valuation(formule, seed=None)` renvoie `(True, valuation)` ou `(False, None)`.
La valuation retournée par cette fonction peut être partielle ; la commande
complète les variables restantes à `False`.

Le benchmark accepte un fichier DIMACS isolé ou le dossier `public-instances`.
Dans ce dernier cas, il mesure les 30 fichiers `public-*.cnf` et contrôle les
statuts SAT/UNSAT avec `expected.json`. Certaines instances peuvent demander
plusieurs dizaines de secondes, voire davantage, au DPLL de base. Le mode
`optimized` appartient à la question 6 et n'est pas implémenté ici.

## Question 3 — Solution d'une grille

```sh
python3 question3/solution.py grilles/grille.txt question3/solution_grille.txt --seed 0
python3 -m unittest -v question3.test_solution
```

Le programme convertit la grille en DIMACS, appelle le solveur de la question 2,
vérifie toutes les règles du jeu sur la valuation obtenue, puis recopie la grille
et ajoute les coordonnées 1-based des chats ainsi qu'une vue utilisant `*`.

## Question 4 — Heuristiques de branchement

```sh
python3 question4/heuristiques.py instances/grille.cnf --heuristique h7 --output-model
python3 -m unittest -v question4.test_heuristiques
```

Les choix disponibles sont `h0` (aléatoire), `h1` (première variable libre),
`h3` (littéral le plus fréquent), `h4` (variable fréquente dans les clauses
minimales) et `h7` (pondération de Jeroslow–Wang). Les trois derniers sont
recalculés dynamiquement sur la formule courante.

## Question 5 — Comparaison des heuristiques

```sh
python3 question5/instances_meowdoku.py
python3 question5/benchmark_q5.py mesurer --limite 10 --graines-h0 3 > question5/resultats_q5.csv
python3 question5/benchmark_q5.py resumer question5/resultats_q5.csv
python3 -m unittest -v question5.test_instrumentation
```

Les compteurs suivent les lignes de l'algorithme 3 : décisions (ligne 17),
retours arrière (ligne 21), propagations unitaires (ligne 5) et littéraux purs
(ligne 11). S'y ajoutent le temps CPU, la part de ce temps passée dans
l'heuristique, le nombre de nœuds et la profondeur maximale. `h3s` et `h7s` sont
les variantes statiques de H3 et H7, utilisées pour mesurer l'apport du recalcul
dynamique. Chaque exécution est interrompue au-delà de `--limite` secondes CPU.
