# Question 6.4 - contrainte redondante par région

Le modèle `cells` est mesuré avec et sans une clause `atLeastOne` par région. Le compilateur, l'encodage `pairwise`, l'heuristique DPLL et les instances restent identiques. Les valeurs sont des médianes ; les compteurs de recherche excluent les timeouts.

| N | variante | instances | SAT/exécutions | compilation (ms) | variables | clauses | longues | résolution (ms) | décisions | retours | propagations |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | avec | 2 | 6/6 | 10.7 | 36 | 366 | 17 | 1.4 | 4 | 2 | 42 |
| 6 | sans | 2 | 6/6 | 8.5 | 36 | 360 | 12 | 1.6 | 6 | 3 | 60 |
| 8 | avec | 2 | 6/6 | 24.0 | 64 | 896 | 22 | 3.8 | 4 | 1 | 72 |
| 8 | sans | 2 | 6/6 | 19.7 | 64 | 888 | 16 | 20.2 | 30 | 24 | 494 |
| 10 | avec | 2 | 6/6 | 47.9 | 100 | 1662 | 29 | 15.9 | 8 | 4 | 118 |
| 10 | sans | 2 | 6/6 | 40.8 | 100 | 1652 | 20 | 685.1 | 2663 | 2656 | 30314 |
| 12 | avec | 2 | 6/6 | 88.2 | 144 | 3018 | 34 | 45.7 | 14 | 8 | 170 |
| 12 | sans | 2 | 6/6 | 79.7 | 144 | 3006 | 24 | 2565.7 | 2136 | 2126 | 38398 |
| 14 | avec | 2 | 6/6 | 151.0 | 196 | 4726 | 41 | 93.1 | 28 | 18 | 360 |
| 14 | sans | 2 | 6/6 | 136.8 | 196 | 4712 | 28 | 7458.2 | 9332 | 9321 | 154180 |

## Effet de la contrainte redondante

Le gain est le ratio `sans / avec` : une valeur supérieure à 1 indique que la variante redondante demande moins de temps ou de recherche.

| N | Δ variables | Δ clauses | gain résolution | gain décisions | gain retours |
|---:|---:|---:|---:|---:|---:|
| 6 | 0 | 6 | 1.11x | 1.22x | 1.20x |
| 8 | 0 | 8 | 5.35x | 7.38x | 24.50x |
| 10 | 0 | 10 | 43.09x | 313.29x | 758.86x |
| 12 | 0 | 12 | 56.18x | 152.57x | 283.53x |
| 14 | 0 | 14 | 80.09x | 339.35x | 532.63x |

Dans cette campagne, la variante redondante est plus rapide pour 5 tailles sur 5 mesurées. Le gain médian selon la taille va de 1.11x à 80.09x.

Les gains de recherche ne sont pas calculés si une variante subit un timeout, car les médianes ne porteraient plus sur les mêmes exécutions.

## Interprétation

Il y a exactement `N` chats grâce aux contraintes de lignes et `K=N` régions contenant chacune au plus un chat. Par le principe des tiroirs, chaque région contient donc déjà un chat : les nouvelles clauses ne changent pas l'ensemble des solutions.

La variante `avec` ajoute une grande disjonction par région, donc `K` clauses et aucune variable SAT. Ces clauses peuvent détecter plus tôt qu'une région n'a plus qu'une case possible et provoquer une propagation unitaire. Elles peuvent ainsi réduire les décisions et retours arrière.

Ce renforcement n'est pas gratuit : le DPLL de référence parcourt et recopie la formule pendant la simplification. Les clauses longues ajoutent donc du travail à chaque affectation. Les temps doivent être interprétés avec les compteurs de recherche, et non comme une garantie générale qu'une contrainte redondante accélère SAT.
