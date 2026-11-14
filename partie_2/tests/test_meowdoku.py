"""Tests du convertisseur GRID/ZONES vers les déclarations CSP."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from meowdoku import generer_declarations, lire_description_grille
from semantics import analyse
from syntax import parse


PARTIE_2 = Path(__file__).resolve().parent.parent
RACINE = PARTIE_2.parent
GRILLE_SUJET = RACINE / "partie_1/grilles/grille.txt"


class TestsConversionMeowdoku(unittest.TestCase):
    def test_grille_du_sujet(self) -> None:
        texte = generer_declarations(lire_description_grille(GRILLE_SUJET))
        self.assertEqual(
            texte,
            """const N = 6;
const M = 6;
const K = 6;
enum Zone = { A, B, C, D, E, F };
const region[N][M] = [
    [A, B, C, B, B, D],
    [A, B, B, B, B, D],
    [A, A, B, D, D, D],
    [A, A, A, E, D, D],
    [A, A, A, A, D, D],
    [F, A, D, D, D, D]
];
""",
        )

    def test_ordre_des_zones_k_et_cases_sont_conserves(self) -> None:
        with TemporaryDirectory() as dossier:
            grille = Path(dossier) / "ordre.txt"
            grille.write_text(
                "GRID 2 3\nZONES R3 R1 R2\nR3 R1 R2\nR2 R3 R1\n",
                encoding="utf-8",
            )
            description = lire_description_grille(grille)
            texte = generer_declarations(description)

        self.assertEqual(description.zones, ("R3", "R1", "R2"))
        self.assertIn("const K = 3;", texte)
        self.assertIn("enum Zone = { R3, R1, R2 };", texte)
        self.assertIn("    [R2, R3, R1]", texte)

    def test_sortie_acceptee_par_la_semantique_csp(self) -> None:
        texte = generer_declarations(lire_description_grille(GRILLE_SUJET))
        model = analyse(parse(texte))
        self.assertEqual(model.symbols["N"].values[()], 6)
        self.assertEqual(model.symbols["M"].values[()], 6)
        self.assertEqual(model.symbols["K"].values[()], 6)

    def test_grille_mal_formee(self) -> None:
        with TemporaryDirectory() as dossier:
            grille = Path(dossier) / "invalide.txt"
            grille.write_text("GRID 2 2\nZONES A B\nA B\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "2 lignes de 2 cases"):
                lire_description_grille(grille)

    def test_noms_de_zone_incompatibles(self) -> None:
        for zone, message in [
            ("A-B", "incompatible"),
            ("var", "mot réservé"),
            ("N", "conflit"),
        ]:
            with self.subTest(zone=zone), TemporaryDirectory() as dossier:
                grille = Path(dossier) / "zone.txt"
                grille.write_text(
                    f"GRID 1 1\nZONES {zone}\n{zone}\n", encoding="utf-8"
                )
                description = lire_description_grille(grille)
                with self.assertRaisesRegex(ValueError, message):
                    generer_declarations(description)

    def test_cli_cree_le_fichier(self) -> None:
        with TemporaryDirectory() as dossier:
            sortie = Path(dossier) / "donnees/model.csp"
            resultat = subprocess.run(
                [sys.executable, str(PARTIE_2 / "meowdoku.py"), str(GRILLE_SUJET), str(sortie)],
                capture_output=True,
                text=True,
                check=True,
            )
            texte = sortie.read_text(encoding="utf-8")

        self.assertIn("const region[N][M]", texte)
        self.assertIn("grille 6 × 6, 6 régions", resultat.stdout)
        self.assertEqual(resultat.stderr, "")

    def test_cli_refuse_decraser_entree(self) -> None:
        resultat = subprocess.run(
            [sys.executable, str(PARTIE_2 / "meowdoku.py"), str(GRILLE_SUJET), str(GRILLE_SUJET)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(resultat.returncode, 0)
        self.assertIn("doivent être des fichiers distincts", resultat.stderr)


if __name__ == "__main__":
    unittest.main()
