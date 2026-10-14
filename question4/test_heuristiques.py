"""Validation de DPLL_H et des heuristiques de la question 4."""

import json
from itertools import product
from pathlib import Path
import random
import subprocess
import sys
import unittest

from question2.sat import lire_dimacs, verifier_valuation
from question4.heuristiques import (
    NOMS_HEURISTIQUES,
    dpll_h,
    litteral_jw,
    litteral_plus_frequent,
    premiere_variable_libre,
    variable_frequente_clauses_minimales,
)


RACINE = Path(__file__).resolve().parent.parent


def satisfiable_exhaustif(formule: list[frozenset[int]], n: int) -> bool:
    """Teste toutes les valuations ; utilisé comme oracle indépendant."""
    return any(
        all(any(valeurs[abs(l) - 1] == (l > 0) for l in clause) for clause in formule)
        for valeurs in product((False, True), repeat=n)
    )


class TestsHeuristiques(unittest.TestCase):
    def verifier_toutes(self, formule: list[frozenset[int]], attendu: bool) -> None:
        copie = list(formule)
        for heuristique in NOMS_HEURISTIQUES:
            with self.subTest(heuristique=heuristique):
                statut, valuation = dpll_h(formule, heuristique, seed=0)
                self.assertEqual(statut, attendu)
                if statut:
                    self.assertIsNotNone(valuation)
                    self.assertTrue(verifier_valuation(formule, valuation))
                else:
                    self.assertIsNone(valuation)
        self.assertEqual(formule, copie)

    def test_choix_des_heuristiques(self) -> None:
        formule = [
            frozenset([1, 2, -4]),
            frozenset([2, 3]),
            frozenset([1, -2, 4, -5]),
        ]
        self.assertEqual(premiere_variable_libre(formule), 1)
        self.assertEqual(litteral_plus_frequent(formule), 1)
        self.assertEqual(variable_frequente_clauses_minimales(formule), 2)
        self.assertEqual(litteral_jw(formule), 2)
        self.assertEqual(
            litteral_plus_frequent([frozenset([-1, -1, 2]), frozenset([-1, 3])]),
            -1,
        )

    def test_toutes_les_formules_sur_deux_variables(self) -> None:
        clauses = [
            frozenset(p * signe for p, signe in enumerate(signes, 1) if signe)
            for signes in product((-1, 0, 1), repeat=2)
        ]
        for masque in range(1 << len(clauses)):
            formule = [c for i, c in enumerate(clauses) if masque & (1 << i)]
            with self.subTest(masque=masque):
                self.verifier_toutes(formule, satisfiable_exhaustif(formule, 2))

    def test_formules_aleatoires_de_la_question_2(self) -> None:
        aleatoire = random.Random(2026)
        for numero in range(100):
            n = aleatoire.randint(1, 6)
            formule = [
                frozenset(
                    aleatoire.choice((-1, 1)) * aleatoire.randint(1, n)
                    for _ in range(aleatoire.randint(1, 4))
                )
                for _ in range(aleatoire.randint(0, 20))
            ]
            with self.subTest(numero=numero):
                self.verifier_toutes(formule, satisfiable_exhaustif(formule, n))

    def test_instances_publiques_elementaires(self) -> None:
        attendus = json.loads(
            (RACINE / "public-instances/expected.json").read_text(encoding="utf-8")
        )
        noms = [nom for nom in attendus if not nom.startswith("public-")]
        for nom in noms:
            _, formule = lire_dimacs(RACINE / "public-instances/instances" / nom)
            self.verifier_toutes(formule, attendus[nom] == "SAT")

    def test_grille_meowdoku(self) -> None:
        _, formule = lire_dimacs(RACINE / "instances/grille.cnf")
        self.verifier_toutes(formule, True)

    def test_cli_et_modele(self) -> None:
        resultat = subprocess.run(
            [
                sys.executable,
                str(RACINE / "question4/heuristiques.py"),
                str(RACINE / "instances/grille.cnf"),
                "--heuristique",
                "h7",
                "--output-model",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        lignes = resultat.stdout.splitlines()
        self.assertEqual(lignes[0], "s SATISFIABLE")
        self.assertEqual((lignes[1].split()[0], lignes[1].split()[-1]), ("v", "0"))
        self.assertEqual(resultat.stderr, "")


if __name__ == "__main__":
    unittest.main()
