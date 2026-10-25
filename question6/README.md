# Question 6 — Organisation du code

- `__init__.py` expose uniquement `dpll_optimized` afin de fournir une interface
  Python minimale.
- `structures.py` centralise les types et l'état mutable pour éviter de
  disperser la représentation interne du solveur.
- `preprocessing.py` normalise la CNF une seule fois afin de retirer les
  tautologies et doublons sans modifier sa satisfiabilité.
- `propagation.py` regroupe le trail, les niveaux de décision et les littéraux
  surveillés afin d'éviter de recopier la formule ; le trail est la pile
  chronologique des affectations, que le retour arrière dépile pour libérer les
  variables d'un niveau abandonné.
- `branching.py` isole le choix heuristique afin d'utiliser H1 sur les structures
  Meowdoku et H4/MOMS sur les formules générales.
- `solver.py` orchestre la propagation, le branchement et le retour arrière
  sans mélanger ces mécanismes.
- `test_optimized.py` contient les contrôles de correction utilisés pendant la
  validation.
- `benchmark_q6.py` exécute et vérifie les variantes comparées pendant
  l'évaluation.
- `resultats_q6.csv` conserve les mesures brutes et les contrôles de correction
  des 220 exécutions.
- `rapport_q6.md` décrit le protocole, synthétise les résultats et justifie le
  choix adaptatif final.
