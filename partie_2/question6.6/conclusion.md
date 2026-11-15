# Question 6.6 — Conclusion générale

Dans nos expériences, **la modélisation a globalement plus d'effet sur le
temps de résolution que les optimisations du solveur**. Elle détermine la
taille et la structure de la FNC, donc à la fois le coût de chaque étape de
recherche et la capacité du solveur à propager rapidement les contraintes.

## Choix du modèle

Le modèle `cells` est environ **6 à 14 fois plus rapide** que le modèle
`positions` sur les tailles pour lesquelles les deux terminent. À `N = 14`,
`positions` dépasse la limite de temps sur toutes les exécutions, alors que
`cells` termine en environ 7,3 s. Le modèle `positions` produit entre **5,7 et
14,7 fois plus de clauses**, dont une proportion importante de clauses
longues, tandis que les clauses de `cells` sont presque toutes binaires.

Le nombre de retours arrière ne suffit cependant pas à expliquer ces écarts.
À `N = 10`, `positions` effectue 364 retours contre 2 656 pour `cells`, mais
reste environ 14 fois plus lent. Une décision coûte beaucoup plus cher dans sa
FNC, car le solveur doit traiter davantage de clauses, souvent plus longues.
Le temps dépend donc à la fois de la taille de l'arbre de recherche et du coût
de traitement de chaque nœud.

## Contraintes redondantes

L'ajout d'une contrainte `atLeastOne` par région ne change pas les solutions,
mais rend explicite une propriété qui était seulement une conséquence globale
des autres contraintes. Ces quelques clauses supplémentaires facilitent la
propagation unitaire.

Le gain croît avec la taille : il va de **1,1 à 80 fois sur le temps de
résolution** et d'environ **1,2 à 759 fois sur les retours arrière** selon les
médianes par taille. À `N = 14`, le temps passe de 7,46 s à 93 ms et les
retours arrière de 9 321 à 18, soit environ **80 fois moins de temps** et
**518 fois moins de retours**. Une formule légèrement plus grande peut donc
être beaucoup plus facile si ses contraintes exposent mieux les conséquences
logiques utiles au solveur.

## Heuristiques et optimisations du solveur

Les heuristiques restent importantes, mais aucune ne domine sur toutes les
familles. Sur les instances publiques UNSAT, H4/MOMS est environ **30 fois
plus rapide** que le choix aléatoire H0 et réduit les retours arrière de 7 988
à 934, soit un facteur **8,6**. Sur les Meowdoku UNSAT, H1 est mieux adaptée à
la structure de l'encodage : elle apporte un gain de temps d'environ **2,7** et
réduit les retours de 4 751 à 1 221, soit un facteur **3,9**. Sur les instances
publiques SAT communes, H4 apporte environ un facteur **2,9** en temps et
environ **12** sur les retours arrière.

La partie I ne s'est pas limitée aux heuristiques. Le solveur final utilise :

- deux littéraux surveillés pour limiter les clauses examinées pendant la
  propagation ;
- un trail et des niveaux de décision pour annuler uniquement les affectations
  de la branche abandonnée ;
- une représentation incrémentale qui évite de recopier toute la formule à
  chaque appel récursif ;
- un prétraitement supprimant les tautologies et les doublons ;
- une sélection adaptative de H1 pour Meowdoku et de H4/MOMS pour les autres
  formules.

Sur le benchmark final, cette combinaison fait passer le nombre de timeouts de
4 à 1 sur 55 instances. Sur les 51 instances résolues par toutes les variantes,
H1 optimisé divise approximativement par deux le temps cumulé du DPLL initial.
Cette campagne mélange toutefois l'amélioration du moteur et le changement
d'heuristique : elle ne permet pas d'attribuer ce facteur aux seuls littéraux
surveillés.

## Bilan

L'ordre d'importance observé est donc d'abord **la qualité du modèle et de son
encodage**, puis **les contraintes redondantes favorisant la propagation**, et
enfin **l'heuristique et l'implémentation du solveur**. Les contraintes
redondantes font elles-mêmes partie de la modélisation : elles montrent qu'un
bon modèle ne doit pas seulement contenir assez d'information pour décrire les
solutions, mais aussi présenter cette information sous une forme directement
exploitable par la propagation.

En résumé, un solveur optimisé parcourt plus efficacement l'arbre de recherche,
mais le modèle détermine en grande partie la taille, la structure et le coût de
cet arbre. **Il faut donc d'abord construire une FNC compacte et propice à la
propagation, puis choisir une heuristique adaptée à sa structure.**
