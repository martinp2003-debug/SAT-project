# Question 6.5 — généralisation du second modèle

Le modèle `cells` utilise une variable booléenne par case. Pour rendre `N`,
`M` et `K` indépendants, il impose exactement un chat par région et seulement
au plus un chat par ligne et par colonne. Les contraintes de voisinage restent
inchangées.

## Vérification indépendante

La recherche de référence énumère le produit cartésien des cases des régions :
chaque candidat contient donc une case par région. Elle valide ensuite le
placement avec `verifier_solution`. Elle ne compile aucun CSP et n'appelle
aucun solveur SAT.

| Grille | N | M | K | Compilateur + DPLL | Exhaustif |
|---|---:|---:|---:|---|---|
| `sat_k_libre.txt` | 4 | 4 | 2 | SAT | SAT |
| `sat_rectangulaire.txt` | 3 | 4 | 2 | SAT | SAT |
| `unsat_k_trop_grand.txt` | 2 | 3 | 3 | UNSAT | UNSAT |
| `unsat_voisinage.txt` | 2 | 2 | 2 | UNSAT | UNSAT |

Les deux méthodes concordent sur les quatre instances. La troisième isole
l'impossibilité de placer `K` chats sur des lignes distinctes lorsque `K > N` ;
la quatrième est impossible à cause du voisinage, indépendamment du comptage.
Cette validation exhaustive est limitée aux petites grilles, car son nombre de
candidats est le produit des tailles des régions.

Commande reproductible :

```sh
uv --directory partie_2 run python question6.5/generalisation_q65.py
```
