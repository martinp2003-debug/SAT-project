"""Tests ciblés du solveur optimisé et de son interface."""

from itertools import product
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from question2.sat import Clause, verifier_valuation
from question6.benchmark_q6 import analyser_sortie, lister_instances
from question6.branching import choisir_strategie
from question6.preprocessing import preprocesser
from question6.propagation import (
    affecter,
    annuler_niveau,
    initialiser_etat,
    ouvrir_niveau,
    propager,
)
from question6.solver import dpll_optimized
from question6.structures import StrategieBranchement


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

    def test_pretraitement_sans_mutation(self) -> None:
        formule = [
            frozenset([1, -1, 2]),
            frozenset([2, 2]),
            frozenset([2]),
        ]
        copie = list(formule)
        probleme = preprocesser(formule, 2)
        self.assertEqual(probleme.clauses, ((2,),))
        self.assertEqual(formule, copie)

    def test_trail_et_retours_arriere(self) -> None:
        formule = [
            frozenset([4]),
            frozenset([1, 2]),
            frozenset([1, -2]),
            frozenset([-1, 3]),
            frozenset([-1, -3]),
        ]
        etat = initialiser_etat(preprocesser(formule, 4))
        self.assertTrue(propager(etat))
        self.assertEqual(etat.trail, [4])
        for choix in (1, -1):
            ouvrir_niveau(etat)
            self.assertTrue(affecter(etat, choix))
            self.assertFalse(propager(etat))
            annuler_niveau(etat)
            self.assertEqual(etat.trail, [4])
            self.assertEqual(etat.affectations[4], 1)
            self.assertTrue(all(etat.affectations[p] == -1 for p in (1, 2, 3)))

    def test_formules_aleatoires_et_strategies(self) -> None:
        aleatoire = random.Random(2026)
        strategies: tuple[StrategieBranchement | None, ...] = (None, "h1", "h4")
        for numero in range(500):
            nombre_variables = aleatoire.randint(1, 6)
            formule = [
                frozenset(
                    aleatoire.choice((-1, 1))
                    * aleatoire.randint(1, nombre_variables)
                    for _ in range(aleatoire.randint(0, 5))
                )
                for _ in range(aleatoire.randint(0, 25))
            ]
            attendu = satisfiable_exhaustif(formule, nombre_variables)
            for strategie in strategies:
                with self.subTest(numero=numero, strategie=strategie):
                    statut, valuation = dpll_optimized(
                        formule, nombre_variables, strategie
                    )
                    self.assertEqual(statut, attendu)
                    if statut:
                        self.assertTrue(verifier_valuation(formule, valuation or {}))

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

    def test_cli_par_defaut_et_unsat(self) -> None:
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "unsat.cnf"
            chemin.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="utf-8")
            resultat = subprocess.run(
                [sys.executable, str(RACINE / "sat.py"), str(chemin)],
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(resultat.stdout, "s UNSATISFIABLE\n")
        self.assertEqual(resultat.stderr, "")
        self.assertEqual(analyser_sortie(resultat.stdout, 1), (False, None))

    def test_lot_du_benchmark(self) -> None:
        instances = lister_instances(
            RACINE / "public-instances", RACINE / "instances/q5"
        )
        self.assertEqual(len(instances), 55)
        self.assertEqual(
            {famille for _, famille, _ in instances},
            {"public", "meowdoku"},
        )


if __name__ == "__main__":
    unittest.main()
