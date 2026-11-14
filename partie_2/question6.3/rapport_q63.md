# Question 6.3 - comparaison des modèles Meowdoku

Toutes les lignes utilisent le même compilateur, le même encodage de `atMostOne` et la même heuristique DPLL. Les valeurs sont des médianes ; les compteurs de recherche excluent les exécutions interrompues.

| N | modèle | instances | SAT/exécutions | compilation (ms) | variables | clauses | binaires | résolution (ms) | décisions | retours | propagations |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | cells | 2 | 6/6 | 21.3 | 36 | 360 | 96.7% | 3.9 | 6 | 3 | 60 |
| 6 | positions | 2 | 6/6 | 141.1 | 72 | 2052 | 26.3% | 54.4 | 18 | 12 | 226 |
| 8 | cells | 2 | 6/6 | 38.5 | 64 | 888 | 98.2% | 37.4 | 30 | 24 | 494 |
| 8 | positions | 2 | 6/6 | 464.5 | 128 | 6848 | 19.6% | 230.0 | 18 | 10 | 286 |
| 10 | cells | 2 | 6/6 | 82.8 | 100 | 1652 | 98.8% | 1304.1 | 2663 | 2656 | 30314 |
| 10 | positions | 2 | 6/6 | 1597.6 | 200 | 17300 | 15.6% | 18398.0 | 375 | 364 | 7235 |
| 12 | cells | 2 | 6/6 | 152.2 | 144 | 3006 | 99.2% | 5077.1 | 2136 | 2126 | 38398 |
| 12 | positions | 2 | 3/6 | 3365.8 | 288 | 36720 | 12.9% | 8894.0 | 26 | 11 | 571 |
| 14 | cells | 2 | 6/6 | 136.7 | 196 | 4712 | 99.4% | 7342.5 | 9332 | 9321 | 154180 |
| 14 | positions | 2 | 0/6 | 4831.7 | 392 | 69188 | 11.0% | - | - | - | - |

## Ratios positions / cells

Un ratio supérieur à 1 signifie que le modèle `positions` est plus grand ou plus coûteux pour la mesure concernée.

| N | clauses | résolution | décisions |
|---:|---:|---:|---:|
| 6 | 5.71x | 14.00x | 3.27x |
| 8 | 7.72x | 6.16x | 0.63x |
| 10 | 10.47x | 14.11x | 0.14x |
| 12 | 12.21x | - | - |
| 14 | 14.68x | - | - |

Les ratios de recherche ne sont pas calculés lorsqu'un des deux modèles a subi un timeout : les médianes ne porteraient alors pas sur les mêmes instances.

## Interprétation

Le compilateur et le solveur sont identiques, mais ils ne reçoivent pas la même FNC. Le modèle `positions` encode deux coordonnées de domaine `1..N` par région, soit `2N^2` variables SAT nommées. Ses contraintes de voisinage peuvent produire un nombre de clauses en ordre `N^4`. Le modèle `cells` utilise directement `N^2` booléens et, pour des régions équilibrées, un nombre de clauses plutôt en ordre `N^3`.

La structure compte autant que la taille. Les clauses du modèle `cells` sont presque toutes binaires, tandis que `positions` contient beaucoup de clauses longues issues des quatre égalités de coordonnées. Cela modifie les propagations unitaires, l'ordre des choix et donc l'arbre DPLL.

Enfin, une décision n'a pas un coût constant dans ce solveur : chaque affectation appelle `simplifier`, qui parcourt et recopie la formule courante. Une grande FNC peut donc prendre plus de temps avec moins de décisions. Les compteurs de recherche doivent toujours être lus avec le nombre et la longueur des clauses.
