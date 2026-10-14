# Question 2 — Lecture DIMACS et algorithmes DPLL

## 1. Représentation des formules

Le programme `question2/sat.py` utilise uniquement la bibliothèque standard de Python.
Un littéral est un entier non nul : `p` représente la variable `p`, et `-p`
sa négation. Une clause est un `frozenset` de littéraux, et une formule est une
liste de clauses. Cette représentation supprime les répétitions d'un même
littéral dans une clause et évite de modifier accidentellement les clauses
partagées entre branches. Les clauses identiques restent présentes.

La distinction entre les deux cas terminaux est essentielle :

- `[]` est la conjonction vide, donc vraie ;
- `[frozenset()]` contient une clause vide, donc est insatisfiable.

`lire_dimacs` ignore les commentaires et les lignes blanches, impose un unique
en-tête `p cnf n m`, vérifie les bornes des identifiants et le nombre de clauses.
Le zéro est un séparateur, pas un littéral. Le lecteur accepte aussi une clause
sur plusieurs lignes ou plusieurs clauses sur une ligne. Il conserve les
clauses vides et rejette une clause sans zéro final.

## 2. Les deux versions de DPLL

Les fonctions `dpll` et `dpll_valuation` implémentent respectivement les
algorithmes 1 et 2 du sujet. Elles utilisent les mêmes opérations :

1. Si une clause est vide, renvoyer UNSAT.
2. Si la formule est vide, renvoyer SAT.
3. S'il existe une clause unitaire, rendre son littéral vrai.
4. Sinon, s'il existe un littéral pur, le rendre vrai.
5. Sinon, choisir uniformément une variable présente et une valeur de vérité ;
   explorer cette affectation, puis son contraire si la première branche échoue.

La simplification `simplifier(F, l)` supprime toutes les clauses contenant `l`,
puis retire `-l` des clauses restantes. Une nouvelle liste est créée ; la formule
initiale reste disponible pour l'autre branche et pour la vérification finale.

Les successions de propagations unitaires et d'éliminations de littéraux purs
sont écrites avec une boucle, équivalente aux appels récursifs du sujet.
La récursion est conservée pour les décisions. La première clause unitaire
est choisie dans l'ordre du fichier ; parmi les littéraux purs, celui dont
l'identifiant est le plus petit est choisi. Ces règles rendent les étapes
forcées déterministes. Seules les décisions sont aléatoires, avec une graine
facultative pour reproduire une exécution.

La version 1 renvoie seulement un booléen. La version 2 renvoie un couple
`(statut, valuation)`, où la valuation est un dictionnaire
`{identifiant: bool}` en cas de succès et `None` en cas d'échec. Les affectations
d'une branche qui échoue ne sont pas conservées. Une valuation partielle est
suffisante dès que toutes les clauses sont satisfaites. Pour l'affichage DIMACS,
les variables absentes sont fixées à `False`, puis chaque clause initiale est
vérifiée directement.

La terminaison repose sur le fait que chaque simplification affecte une variable
encore présente, qui disparaît de la formule restante. Les propagations unitaires
sont nécessaires, l'élimination d'un littéral pur préserve la satisfiabilité, et
les deux branches couvrent les deux valeurs possibles de la variable choisie.

## 3. Validation et résultat sur `instances/grille.cnf`

L'instance contient **36 variables et 408 clauses**. Les deux versions renvoient
**SAT**. Pour la graine 0, les variables vraies sont :

```text
3 11 14 22 30 31
```

Toutes les autres variables sont fausses. Avec la correspondance de la question 1,
les chats occupent les cases suivantes (indices à partir de 1) :

| Région | Ligne | Colonne |
| --- | ---: | ---: |
| A | 3 | 2 |
| B | 2 | 5 |
| C | 1 | 3 |
| D | 5 | 6 |
| E | 4 | 4 |
| F | 6 | 1 |

La valuation satisfait les 408 clauses. Un contrôle séparé vérifie les règles
du jeu : six chats, un par région, des lignes et colonnes distinctes, et aucune
adjacence entre chats. Ce placement correspond à celui de la figure 2 du sujet.

La commande `python3 -m unittest -v` exécute **10 tests**, tous réussis :

- Cas élémentaires SAT et UNSAT : formule vide, clause vide, unités opposées,
  propagation jusqu'à une contradiction, littéraux purs, tautologie et lampes
  du sujet ; exercices de branchement et de retour arrière.
- Comparaison des deux versions avec l'énumération exhaustive des valuations
  pour les 512 formules formées à partir des 9 clauses sans tautologie sur deux
  variables, clause vide comprise.
- Même comparaison sur 300 formules pseudo-aléatoires comportant de 1 à 6
  variables, avec contrôle des valuations SAT et de l'absence de modification
  des formules d'entrée.
- Validation de `grille.cnf` sur 20 graines, des règles du jeu, du lecteur DIMACS,
  du rejet d'entrées incorrectes et du format de sortie de la commande.

Le dossier `public-instances` fourni par les enseignants est présent dans le
projet. Il contient 30 instances de benchmark `public-01.cnf` à
`public-30.cnf`, ainsi que des tests plus petits d'interface et de cas limites.
Le fichier `expected.json` fournit le statut SAT/UNSAT attendu pour chacune.
Le script de benchmark utilise ces statuts pour détecter un résultat incorrect.

## 4. Mesures et commentaire des performances

Commande de mesure :

```sh
python3 question2/benchmark_q2.py public-instances --repetitions 100 --limite 2
```

Pour chaque instance, les deux versions utilisent les mêmes graines et leur
ordre est alterné entre répétitions. Le temps CPU est mesuré par `process_time_ns`,
uniquement autour de l'appel au solveur. La lecture DIMACS, le lancement de
Python, l'affichage et la vérification des modèles sont exclus. La création du
générateur aléatoire est incluse. Les résultats sont donc des temps de résolution,
pas les temps complets qu'utilisera la compétition de la question 6.

Une exécution rapide peut être limitée aux premiers fichiers avec `--limite`.
L'essai sur le lot complet montre que `public-03.cnf` demande déjà plus d'une
minute au DPLL de base ; les 30 instances ne constituent donc pas un test court.

Mesures locales du 14 octobre 2026, Python 3.11.5, macOS/Darwin 25.6.0, ARM64,
conservées dans `question2/resultats_q2.csv` :

| Instance | Version | Résultat | Répétitions | Médiane CPU (ms) | Minimum (ms) | Maximum (ms) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| public-01 | 1 — statut | SAT | 100 | 2,1590 | 0,9260 | 4,7600 |
| public-01 | 2 — valuation | SAT | 100 | 2,2630 | 0,8890 | 5,4390 |
| public-02 | 1 — statut | SAT | 100 | 3,0315 | 1,9580 | 64,3100 |
| public-02 | 2 — valuation | SAT | 100 | 3,1340 | 1,9460 | 65,2010 |

Les deux versions donnent les statuts attendus et ont des médianes proches.
La construction de la valuation ajoute ici un faible surcoût médian. Les maxima
nettement plus élevés sur `public-02` montrent que les choix aléatoires peuvent
conduire à des arbres de recherche de tailles très différentes selon la graine.
Ces deux instances restent faciles. En revanche, l'essai de `public-03` avec la
graine 0 n'avait toujours pas terminé après une minute et a été interrompu ; il
n'apparaît donc pas dans le CSV, qui ne contient que des mesures complètes.

Si `L` est le nombre total d'occurrences de littéraux dans la formule courante,
une simplification ou une recherche de littéraux purs parcourt la formule en
temps de l'ordre de `L` (avec les opérations usuelles sur les ensembles).
Le tri des variables au moment d'une décision ajoute un coût en `O(n log n)`.
Le nombre de branches peut être exponentiel en nombre de variables : le bon
temps obtenu ici ne constitue donc pas une garantie sur de grandes instances.
Les copies de formules consomment aussi de la mémoire. Enfin, la récursion de
branchement reste soumise à la limite de profondeur de Python ; la boucle des
propagations évite ce problème pour de longues suites d'affectations forcées.

## 5. Périmètre et assistance

Le point d'entrée `question2/sat.py` reprend dès maintenant le format de sortie imposé
en fin de sujet et accepte `--mode dpll`. Le mode `optimized` relève de la
question 6 et n'est pas réalisé dans cette question.

Le code, les tests et ce compte rendu ont été préparés avec l'aide de Codex.
