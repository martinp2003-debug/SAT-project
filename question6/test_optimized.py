"""Tests ciblés du solveur optimisé et de son interface."""

from itertools import product
from pathlib import Path
import subprocess
import sys
import unittest

from question2.sat import Clause, verifier_valuation
from question6.branching import choisir_strategie
from question6.preprocessing import preprocesser
from question6.solver import dpll_optimized


RACINE = Path(__file__).resolve().parent.parent


def satisfiable_exhaustif(formule: list[Clause], nombre_variables: int) -> bool:
    """Calcule le statut par énumération pour servir d'oracle indépendant."""
    return any(
        all(
            any(valeurs[abs(litteral) - 1] == (litteral > 0) for litteral in clause)
            for clause in formule
        )
        for valeurs in product((False, True), repeat=nombre_variables)
    )


class TestsSolveurOptimise(unittest.TestCase):
    """Valide le cœur incrémental sur de petites formules exhaustives."""

    def test_toutes_les_formules_sur_deux_variables(self) -> None:
        clauses = [
            frozenset(
                variable * signe
                for variable, signe in enumerate(signes, start=1)
                if signe
            )
            for signes in product((-1, 0, 1), repeat=2)
        ]
        for masque in range(1 << len(clauses)):
            formule = [
                clause
                for indice, clause in enumerate(clauses)
                if masque & (1 << indice)
            ]
            with self.subTest(masque=masque):
                attendu = satisfiable_exhaustif(formule, 2)
                statut, valuation = dpll_optimized(formule, 2)
                self.assertEqual(statut, attendu)
                if statut:
                    self.assertIsNotNone(valuation)
                    self.assertTrue(verifier_valuation(formule, valuation or {}))
                else:
                    self.assertIsNone(valuation)

    def test_choix_adaptatif(self) -> None:
        meowdoku = [
            frozenset([1, 2, 3]),
            frozenset([-1, -2]),
            frozenset([-1, -3]),
            frozenset([-2, -3]),
        ]
        generale = [frozenset([1, -2, 3]), frozenset([-1, 2])]
        self.assertEqual(choisir_strategie(preprocesser(meowdoku, 3)), "h1")
        self.assertEqual(choisir_strategie(preprocesser(generale, 3)), "h4")

    def test_cli_des_deux_modes(self) -> None:
        for mode in ("dpll", "optimized"):
            with self.subTest(mode=mode):
                resultat = subprocess.run(
                    [
                        sys.executable,
                        str(RACINE / "sat.py"),
                        str(RACINE / "instances/grille.cnf"),
                        "--mode",
                        mode,
                        "--output-model",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                lignes = resultat.stdout.splitlines()
                self.assertEqual(lignes[0], "s SATISFIABLE")
                self.assertEqual(
                    (lignes[1].split()[0], lignes[1].split()[-1]),
                    ("v", "0"),
                )
                self.assertEqual(resultat.stderr, "")


if __name__ == "__main__":
    unittest.main()
