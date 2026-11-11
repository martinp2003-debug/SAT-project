# Question 3 — Recherche et restitution d'une solution

Le programme `question3/solution.py` reçoit un fichier de grille et le chemin du
fichier de résultat. Il réutilise volontairement les composants des questions
précédentes selon la chaîne suivante :

1. `lire_grille` valide le format `GRID/ZONES` ;
2. `construire_clauses` encode les règles du Meowdoku ;
3. `ecrire_dimacs` produit un fichier DIMACS temporaire ;
4. `lire_dimacs` relit cette formule dans la représentation du solveur ;
5. `dpll_valuation` cherche une valuation satisfaisante ;
6. les variables vraies sont reconverties en coordonnées de chats.

Le fichier DIMACS est temporaire et automatiquement supprimé après sa lecture.
Le fichier final recopie la grille d'entrée, puis donne une ligne
`REGION LIGNE COLONNE` par région avec des coordonnées commençant à 1. Une
seconde représentation affiche ensuite `*` sur les cases contenant un chat et
`.` sur les autres, comme dans la figure 2 de l'énoncé.

## Validation systématique

La valuation n'est pas acceptée sur la seule confiance du solveur. Le programme
contrôle indépendamment que :

- chaque coordonnée appartient à la grille ;
- toutes les régions, et seulement elles, ont une position associée ;
- la position associée à une région se trouve effectivement dans cette région ;
- deux chats ne partagent ni une ligne, ni une colonne, ni une case ;
- aucune paire de chats n'est voisine horizontalement, verticalement ou en
  diagonale.

Une violation provoque une erreur et empêche l'écriture d'un faux résultat.
Une grille insatisfiable est également signalée explicitement.

## Utilisation et tests

Depuis la racine du projet :

```sh
python3 question3/solution.py grilles/grille.txt question3/solution_grille.txt --seed 0
python3 -m unittest -v question3.test_solution
```

Les tests vérifient la solution exacte de la figure 2, toutes les familles de
contraintes, la recopie du fichier source, les deux formats de sortie, le rejet
d'une grille insatisfiable et l'interface en ligne de commande.
