# Question 5 — Instrumentation et comparaison des heuristiques

## Instrumentation et protocole

`question5/instrumentation.py` reprend `dpll_h` (question 4) en ajoutant des
compteurs. Un test vérifie que le statut et la valuation obtenus sont identiques
à ceux de `dpll_h` : l'instrumentation ne modifie pas la recherche.

| Critère | Mesure |
|---|---|
| décisions (ligne 17) | appels à l'heuristique |
| retours arrière (ligne 21) | essais de la valeur opposée après l'échec de la 1ʳᵉ branche |
| propagations unitaires (ligne 5) / littéraux purs (ligne 11) | règles appliquées |
| temps CPU / ratio heuristique | `process_time_ns` ; part du temps passée dans le choix de branchement |
| autres | nombre de nœuds, profondeur maximale (dans le CSV) |

Pour répondre à la question sur le recalcul dynamique, deux variantes
**statiques** ont été ajoutées : `h3s` et `h7s` classent une seule fois les
littéraux de la formule initiale, puis prennent le premier dont la variable est
encore libre. **H0 est exactement l'algorithme 2** (même tirage aléatoire) et sert
de référence ; il est exécuté avec 3 graines, dont on retient la médiane.

**Instances (55).**

- 30 instances publiques (19 SAT, 11 UNSAT), issues de SATLIB.
- 25 instances Meowdoku générées par `question5/instances_meowdoku.py` à partir
  du code de la question 1 :
  - 11 SAT : la grille du sujet, plus des grilles de taille 6 à 14 ;
  - 14 UNSAT : des grilles de taille 4 à 10 dont la plus grande région est coupée
    en deux. Il faut alors N + 1 chats sur N lignes, ce qui est impossible
    (principe des tiroirs).

Chaque exécution est limitée à 10 s CPU. Les réponses et les modèles sont
vérifiés : aucune erreur sur les 495 exécutions. Les totaux ne portent que sur
les instances résolues par **toutes** les heuristiques, pour ne pas avantager
celles qui échouent sur les instances difficiles. Les mesures brutes sont dans
`question5/resultats_q5.csv`.

```sh
python3 question5/benchmark_q5.py mesurer --limite 10 --graines-h0 3 > question5/resultats_q5.csv
python3 question5/benchmark_q5.py resumer question5/resultats_q5.csv
```

## Résultats

**Instances résolues en moins de 10 s**

| | h0 | h1 | h3 | h4 | h7 | h3s | h7s |
|---|---|---|---|---|---|---|---|
| Public SAT (19) | 14 | 16 | 13 | **17** | 13 | **17** | 16 |
| Public UNSAT (11) | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| Meowdoku SAT (11) | 11 | 11 | 11 | 11 | 11 | 10 | 10 |
| Meowdoku UNSAT (14) | 14 | 14 | 14 | 14 | 14 | 14 | 14 |

**Temps CPU total en ms (et nombre de décisions) sur les instances communes**

| | h0 | h1 | h3 | h4 | h7 | h3s | h7s |
|---|---|---|---|---|---|---|---|
| Public SAT (12) | 1685 (1166) | 2092 (1530) | 994 (387) | **575 (259)** | 622 (332) | 1257 (479) | 617 (285) |
| Public UNSAT (10) | 12836 (7988) | 9296 (5222) | 4033 (2269) | **430 (934)** | 602 (1036) | 6357 (3417) | 680 (1213) |
| Meowdoku SAT (10) | 504 (516) | **361 (149)** | 571 (684) | 541 (598) | 586 (684) | 2814 (2559) | 2802 (2559) |
| Meowdoku UNSAT (14) | 3826 (4751) | **1400 (1221)** | 4326 (9470) | 3943 (7045) | 4367 (9470) | 3955 (6482) | 3919 (6482) |
| Ratio heuristique | 5–6 % | 4–6 % | 12–25 % | 6–25 % | 11–27 % | 6–10 % | 6–10 % |

## Analyse

**Observations générales.**

- **En UNSAT, le nombre de retours arrière est toujours égal au nombre de
  décisions** (vérifié sur toutes les exécutions). Dans une formule
  insatisfiable, chaque branchement échoue des deux côtés. En SAT, l'écart entre
  les deux mesure les paris réussis du premier coup : sur les instances publiques
  SAT, h4 fait 90 retours pour 259 décisions, h0 en fait 1079 pour 1166.
- **La règle du littéral pur ne s'applique jamais sur Meowdoku.** Chaque variable
  apparaît positivement dans la clause de sa région et négativement dans les
  clauses « au plus un ».
- **La grille du sujet est résolue sans aucune décision**, par propagation
  unitaire seulement.
- **H0 est instable** : sur `public-06`, une graine résout l'instance en 0,7 s et
  les deux autres dépassent 10 s.

**Les résultats correspondent-ils à nos intuitions ?** Sur les instances
publiques, oui. Les heuristiques qui privilégient les petites clauses (h4 MOMS,
h7 Jeroslow–Wang) sont les meilleures, parce qu'elles font apparaître vite des
clauses unitaires et des conflits. Deux résultats nous ont en revanche surpris :

1. **Sur Meowdoku, h1, la plus simple, est la meilleure.** L'encodage contient
   surtout des clauses binaires négatives `(¬a ∨ ¬b)`. H3 et H7 choisissent donc
   presque toujours « pas de chat dans cette case », un pari qui ne contraint
   presque rien. H1 met la variable à vrai, donc **pose un chat** : la propagation
   élimine aussitôt sa ligne, sa colonne, sa région et les diagonales voisines.
2. **Aucune heuristique ne domine partout.** h3 et h7 échouent sur de grandes
   instances SAT (`public-06`, `public-11`, `public-19`) que h1 ou les variantes
   statiques résolvent. À l'inverse, `public-12` n'est résolue que par h3.

**Gain par rapport à l'algorithme 2.** Il est fort en UNSAT, où tout l'arbre doit
être parcouru :

- instances publiques UNSAT : h4 va **30 fois plus vite** que h0 (12,8 s → 0,4 s)
  et fait 8,6 fois moins de décisions ;
- Meowdoku UNSAT : h1 va 2,7 fois plus vite que h0.

Il est plus modeste en SAT (× 2,9 pour h4 sur les instances publiques, × 1,4 pour
h1 sur Meowdoku), car le hasard peut aussi trouver vite une solution. Une bonne
heuristique résout en revanche davantage d'instances : 17/19 pour h4 contre
14/19 pour h0. Une heuristique inadaptée peut faire **pire** que le hasard : sur
Meowdoku UNSAT, h3 et h7 font deux fois plus de décisions que h0.

**Le recalcul dynamique vaut-il son coût ?** Pour h3 et h7, le recalcul occupe 11 à 27 %
du temps CPU, contre 6 à 10 % pour les variantes statiques. Ce coût reste modéré,
parce que la recopie de la formule à chaque nœud (`simplifier`) domine le temps
total.

- **Utile pour H3** : sur les instances publiques UNSAT, h3 fait 34 % de
  décisions en moins que h3s. Sur Meowdoku SAT, h3 et h7 font environ 680
  décisions contre 2 559 pour les variantes statiques : au départ, toutes les cases
  ont presque le même score, et seul le recalcul tient compte des chats déjà
  posés.
- **Presque inutile pour H7 sur les instances publiques** (622 contre 617 ms en
  SAT) : les clauses y ont toutes la même taille au départ, et l'ordre initial
  reste une bonne approximation.
- **Insuffisant quand le critère est inadapté** : sur Meowdoku UNSAT, les
  variantes statiques font même un peu mieux. Recalculer un mauvais critère ne le
  rend pas meilleur.

**En résumé :** h4 (MOMS) est le meilleur compromis général (52 instances sur 55),
et h1 est le meilleur choix pour Meowdoku.

**Limites.**

- Les temps des heuristiques déterministes sont mesurés une seule fois, donc
  bruités en dessous de quelques millisecondes. Les compteurs, eux, sont exacts.
- Les grilles Meowdoku UNSAT relèvent toutes du principe des tiroirs, donc d'une
  seule forme d'insatisfiabilité.

## Usage d'assistants IA

Un assistant IA (Claude) a été utilisé pour écrire le code d'instrumentation, le
script de mesures et une première version de ce rapport. Les choix et les
analyses ont été relus et discutés par le binôme.
