"""Question 6.5 : généralisation et oracle exhaustif indépendant."""

from pathlib import Path
import subprocess
import sys
import unittest


RACINE = Path(__file__).resolve().parents[2]
PARTIE_2 = RACINE / "partie_2"
DOSSIER_Q65 = PARTIE_2 / "question6.5"
if str(DOSSIER_Q65) not in sys.path:
    sys.path.insert(0, str(DOSSIER_Q65))
if str(PARTIE_2) not in sys.path:
    sys.path.insert(0, str(PARTIE_2))

from generalisation_q65 import (  # noqa: E402
    comparer_avec_exhaustif,
    rechercher_solution_exhaustive,
)
from meowdoku import generer_modele, lire_description_grille  # noqa: E402
from question3.solution import verifier_solution  # noqa: E402


GRILLES = DOSSIER_Q65 / "grilles"
STATUTS = {
    "sat_k_libre.txt": True,
    "sat_rectangulaire.txt": True,
    "unsat_k_trop_grand.txt": False,
    "unsat_voisinage.txt": False,
}


class TestsGeneralisationQ65(unittest.TestCase):
    def test_modele_generalise_exprime_les_bons_cardinaux(self) -> None:
        description = lire_description_grille(GRILLES / "sat_rectangulaire.txt")
        source = generer_modele(description, "cells")
        self.assertIn("constraint atMostOne(cat[i][*])", source)
        self.assertIn("constraint atMostOne(cat[*][j])", source)
        self.assertNotIn("constraint exactlyOne(cat[i][*])", source)
        self.assertEqual(source.count("constraint atLeastOne("), 2)

    def test_recherche_exhaustive_produit_une_solution_metier(self) -> None:
        description = lire_description_grille(GRILLES / "sat_rectangulaire.txt")
        solution = rechercher_solution_exhaustive(description)
        self.assertIsNotNone(solution)
        self.assertTrue(
            verifier_solution(
                [list(ligne) for ligne in description.grille], solution
            )
        )

    def test_sat_et_exhaustif_concordent_sur_les_petites_grilles(self) -> None:
        for nom, attendu in STATUTS.items():
            with self.subTest(grille=nom):
                description = lire_description_grille(GRILLES / nom)
                resultat = comparer_avec_exhaustif(description)
                self.assertEqual(resultat.sat_compilateur, attendu)
                self.assertEqual(resultat.sat_exhaustif, attendu)

    def test_cli_compare_toute_la_campagne(self) -> None:
        resultat = subprocess.run(
            [sys.executable, str(DOSSIER_Q65 / "generalisation_q65.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(resultat.stdout.count("\n"), len(STATUTS) + 1)
        self.assertIn("sat_rectangulaire.txt\t3\t4\t2\tSAT\tSAT", resultat.stdout)
        self.assertIn(
            "unsat_k_trop_grand.txt\t2\t3\t3\tUNSAT\tUNSAT",
            resultat.stdout,
        )


if __name__ == "__main__":
    unittest.main()
