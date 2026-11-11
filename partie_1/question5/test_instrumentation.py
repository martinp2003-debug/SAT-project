"""Validation de l'instrumentation et des instances de la question 5."""

import csv
import io
from itertools import product
from pathlib import Path
import random
import unittest

from question1.conversion import construire_clauses
from question1.generation import generer_grille
from question2.sat import lire_dimacs, verifier_valuation
from question4.heuristiques import dpll_h
from question4.test_heuristiques import satisfiable_exhaustif
from question5.benchmark_q5 import lister_instances, mesurer, resumer
from question5.instances_meowdoku import rendre_insatisfiable
from question5.instrumentation import (
    NOMS_STATIQUES,
    TOUTES_HEURISTIQUES,
    dpll_h_instrumente,
    litteral_force_type,
    ordre_statique,
)


RACINE = Path(__file__).resolve().parent.parent


class TestsInstrumentation(unittest.TestCase):
    def test_meme_exploration_que_la_question_4(self) -> None:
        """Les compteurs ne modifient ni le statut ni le modèle trouvé."""
        aleatoire = random.Random(5)
        for numero in range(100):
            n = aleatoire.randint(1, 6)
            formule = [
                frozenset(
                    aleatoire.choice((-1, 1)) * aleatoire.randint(1, n)
                    for _ in range(aleatoire.randint(1, 4))
                )
                for _ in range(aleatoire.randint(0, 20))
            ]
            for h in ("h0", "h1", "h3", "h4", "h7"):
                with self.subTest(numero=numero, heuristique=h):
                    resultat = dpll_h_instrumente(formule, h, seed=numero)
                    self.assertEqual(
                        (resultat.satisfiable, resultat.valuation),
                        dpll_h(formule, h, seed=numero),
                    )

    def test_toutes_les_heuristiques_sont_correctes(self) -> None:
        clauses = [
            frozenset(p * signe for p, signe in enumerate(signes, 1) if signe)
            for signes in product((-1, 0, 1), repeat=2)
        ]
        for masque in range(1 << len(clauses)):
            formule = [c for i, c in enumerate(clauses) if masque & (1 << i)]
            attendu = satisfiable_exhaustif(formule, 2)
            for h in TOUTES_HEURISTIQUES:
                with self.subTest(masque=masque, heuristique=h):
                    resultat = dpll_h_instrumente(formule, h, seed=0)
                    self.assertEqual(resultat.satisfiable, attendu)
                    if attendu:
                        self.assertTrue(verifier_valuation(formule, resultat.valuation))

    def test_compteurs_sur_un_exemple(self) -> None:
        # (x1 ∨ x2) ∧ (x1 ∨ ¬x2) ∧ (¬x1 ∨ x3) ∧ (¬x1 ∨ ¬x3) est UNSAT.
        # Avec H1 : décision x1, contradiction par propagation ; retour arrière
        # sur ¬x1, puis propagation de x2 et contradiction.
        formule = [frozenset(c) for c in ([1, 2], [1, -2], [-1, 3], [-1, -3])]
        resultat = dpll_h_instrumente(formule, "h1")
        s = resultat.statistiques
        self.assertFalse(resultat.satisfiable)
        self.assertEqual((s.decisions, s.retours_arriere), (1, 1))
        self.assertEqual(s.propagations_unitaires, 2)
        self.assertEqual(s.litteraux_purs, 0)
        self.assertEqual((s.noeuds, s.profondeur_max), (3, 1))
        self.assertLessEqual(s.temps_heuristique_ms, s.temps_cpu_ms)

    def test_regle_du_litteral_pur(self) -> None:
        resultat = dpll_h_instrumente([frozenset([1, 2]), frozenset([1, -2])], "h1")
        self.assertEqual(resultat.statistiques.litteraux_purs, 1)
        self.assertEqual(resultat.statistiques.decisions, 0)
        self.assertEqual(litteral_force_type([frozenset([-3])]), (-3, "unitaire"))
        self.assertIsNone(litteral_force_type([frozenset([1, 2]), frozenset([-1, -2])]))

    def test_ordre_statique(self) -> None:
        formule = [frozenset([1, 2, -4]), frozenset([2, 3]), frozenset([1, -2, 4, -5])]
        self.assertEqual(ordre_statique(formule, "h3s")[0], 1)
        self.assertEqual(ordre_statique(formule, "h7s")[0], 2)
        self.assertEqual(set(NOMS_STATIQUES), {"h3s", "h7s"})

    def test_delai_depasse(self) -> None:
        _, formule = lire_dimacs(RACINE / "instances/q5/meow_unsat_07_s1.cnf")
        resultat = dpll_h_instrumente(formule, "h0", seed=0, limite_s=0)
        self.assertIsNone(resultat.satisfiable)
        self.assertTrue(resultat.statistiques.interrompu)

    def test_grilles_rendues_insatisfiables(self) -> None:
        for taille in (4, 5, 6):
            grille, _ = generer_grille(taille, seed=taille)
            modifiee = rendre_insatisfiable(grille, seed=taille)
            regions = {r for ligne in modifiee for r in ligne}
            self.assertEqual(len(regions), taille + 1)
            formule = [frozenset(c) for c in construire_clauses(modifiee)]
            self.assertFalse(dpll_h_instrumente(formule, "h1").satisfiable)

    def test_instances_et_resume(self) -> None:
        instances = lister_instances(
            RACINE / "public-instances", RACINE / "instances/q5"
        )
        familles = {famille for _, famille, _ in instances}
        self.assertEqual(familles, {"public", "meowdoku"})
        petites = [i for i in instances if i[0].name in ("public-01.cnf", "grille.cnf")]
        sortie = io.StringIO()
        mesurer(petites, ["h1", "h7"], 1, 10.0, sortie)
        lignes = list(csv.DictReader(io.StringIO(sortie.getvalue())))
        self.assertEqual(len(lignes), 4)
        self.assertIn("| h7 | 1/1 |", resumer(lignes, ["h1", "h7"]))


if __name__ == "__main__":
    unittest.main()
