"""Tests de la recherche, de la validation et du format de la question 3."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from question3.solution import (
    ecrire_solution,
    formater_solution,
    resoudre_grille,
    verifier_solution,
)


RACINE = Path(__file__).resolve().parent.parent
GRILLE_SUJET = RACINE / "grilles/grille.txt"


class TestsSolution(unittest.TestCase):
    def test_solution_de_la_figure_2(self) -> None:
        grille, solution = resoudre_grille(GRILLE_SUJET, seed=0)
        self.assertEqual(
            solution,
            {
                "C": (0, 2),
                "B": (1, 4),
                "A": (2, 1),
                "E": (3, 3),
                "D": (4, 5),
                "F": (5, 0),
            },
        )
        self.assertTrue(verifier_solution(grille, solution))
        texte = formater_solution(grille, solution)
        self.assertIn("A 3 2\n", texte)
        self.assertIn("F 6 1\n", texte)
        self.assertTrue(texte.endswith("* . . . . .\n"))

    def test_validateur_rejette_les_solutions_invalides(self) -> None:
        grille, solution = resoudre_grille(GRILLE_SUJET, seed=0)

        sans_region = dict(solution)
        del sans_region["A"]
        self.assertFalse(verifier_solution(grille, sans_region))

        mauvaise_region = dict(solution)
        mauvaise_region["A"] = solution["B"]
        self.assertFalse(verifier_solution(grille, mauvaise_region))

        meme_ligne = dict(solution)
        meme_ligne["A"] = (0, 0)
        self.assertFalse(verifier_solution(grille, meme_ligne))

        voisines = dict(solution)
        voisines["A"] = (1, 0)
        self.assertFalse(verifier_solution(grille, voisines))

    def test_fichier_resultat_reprend_entree_et_deux_formats(self) -> None:
        grille, solution = resoudre_grille(GRILLE_SUJET, seed=0)
        with TemporaryDirectory() as dossier:
            sortie = Path(dossier) / "solution.txt"
            ecrire_solution(GRILLE_SUJET, sortie, grille, solution)
            original = GRILLE_SUJET.read_text(encoding="utf-8")
            resultat = sortie.read_text(encoding="utf-8")
        self.assertTrue(resultat.startswith(original))
        self.assertIn("\nA 3 2\n", resultat)
        self.assertIn("\n. . * . . .\n", resultat)

    def test_grille_insatisfiable(self) -> None:
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "impossible.txt"
            chemin.write_text(
                "GRID 2 2\nZONES A B\nA A\nB B\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "pas de solution"):
                resoudre_grille(chemin, seed=0)

    def test_cli(self) -> None:
        with TemporaryDirectory() as dossier:
            sortie = Path(dossier) / "solution.txt"
            resultat = subprocess.run(
                [
                    sys.executable,
                    str(RACINE / "question3/solution.py"),
                    str(GRILLE_SUJET),
                    str(sortie),
                    "--seed",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(sortie.is_file())
            self.assertIn("solution valide avec 6 chats", resultat.stdout)
            self.assertEqual(resultat.stderr, "")


if __name__ == "__main__":
    unittest.main()
