"""Tests de la conversion et des deux modèles Meowdoku."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from execution import compile_program, solve_encoding
from expansion import Cell
from meowdoku import (
    decoder_solution,
    generer_declarations,
    generer_modele,
    lire_description_grille,
)
from semantics import analyse
from syntax import parse


PARTIE_2 = Path(__file__).resolve().parent.parent
RACINE = PARTIE_2.parent
GRILLE_SUJET = RACINE / "partie_1/grilles/grille.txt"
AUTRE_GRILLE_SAT = RACINE / "partie_1/grilles/q5/meow_sat_06_s1.txt"

if str(RACINE / "partie_1") not in sys.path:
    sys.path.insert(0, str(RACINE / "partie_1"))

from question3.solution import verifier_solution  # noqa: E402


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


class TestsModelesMeowdoku(unittest.TestCase):
    def compiler_et_resoudre(self, grille: Path, representation: str):
        description = lire_description_grille(grille)
        source = generer_modele(description, representation)
        _, _, encoding = compile_program(parse(source))
        satisfiable, values = solve_encoding(encoding)
        self.assertTrue(satisfiable)
        self.assertIsNotNone(values)
        solution = decoder_solution(description, representation, values)
        self.assertTrue(
            verifier_solution([list(row) for row in description.grille], solution)
        )
        return source, solution

    def test_les_deux_modeles_sont_compiles_resolus_et_verifies(self) -> None:
        for grille in (GRILLE_SUJET, AUTRE_GRILLE_SAT):
            for representation in ("positions", "cells"):
                with self.subTest(grille=grille.name, model=representation):
                    source, solution = self.compiler_et_resoudre(grille, representation)
                    self.assertEqual(len(solution), 6)
                    self.assertIn("const region[N][M]", source)

    def test_regle_de_region_du_modele_cases(self) -> None:
        source = generer_modele(lire_description_grille(GRILLE_SUJET), "cells")
        self.assertIn("region[i1][j1] = region[i2][j2]", source)
        self.assertIn("i1 < i2 or (i1 = i2 and j1 < j2)", source)

    def test_les_deux_modeles_reconnaissent_une_grille_insatisfiable(self) -> None:
        # Sur 2 x 2, deux chats de lignes et colonnes distinctes sont forcément
        # voisins en diagonale.
        with TemporaryDirectory() as directory:
            path = Path(directory) / "unsat.txt"
            path.write_text("GRID 2 2\nZONES A B\nA A\nB B\n", encoding="utf-8")
            description = lire_description_grille(path)
            for representation in ("positions", "cells"):
                with self.subTest(model=representation):
                    source = generer_modele(description, representation)
                    _, _, encoding = compile_program(parse(source))
                    satisfiable, values = solve_encoding(encoding)
                    self.assertFalse(satisfiable)
                    self.assertIsNone(values)

    def test_adaptateurs_rejettent_un_decodage_incomplet_ou_ambigu(self) -> None:
        description = lire_description_grille(GRILLE_SUJET)
        with self.assertRaisesRegex(ValueError, "une position par région"):
            decoder_solution(description, "positions", {})

        # (1, 1) et (2, 1) appartiennent toutes deux à la région A.
        values = {Cell("cat", (1, 1)): True, Cell("cat", (2, 1)): True}
        with self.assertRaisesRegex(ValueError, "plusieurs chats.*région A"):
            decoder_solution(description, "cells", values)

    def test_generation_complete_exige_n_egal_m_egal_k(self) -> None:
        cases = [
            "GRID 2 3\nZONES A B\nA A B\nA B B\n",
            "GRID 2 2\nZONES A B C\nA B\nC C\n",
        ]
        for text in cases:
            with self.subTest(text=text), TemporaryDirectory() as directory:
                path = Path(directory) / "grid.txt"
                path.write_text(text, encoding="utf-8")
                description = lire_description_grille(path)
                with self.assertRaisesRegex(ValueError, "N = M = K"):
                    generer_modele(description, "cells")

    def test_generation_complete_refuse_un_nom_utilise_par_les_regles(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "grid.txt"
            path.write_text("GRID 1 1\nZONES i\ni\n", encoding="utf-8")
            description = lire_description_grille(path)
            with self.assertRaisesRegex(ValueError, "conflit avec les règles"):
                generer_modele(description, "positions")

    def test_cli_genere_les_deux_modeles_complets(self) -> None:
        for representation, declaration in (
            ("positions", "array row[Zone]"),
            ("cells", "array cat[N][M]"),
        ):
            with self.subTest(model=representation), TemporaryDirectory() as directory:
                output = Path(directory) / "model.csp"
                result = subprocess.run(
                    [
                        sys.executable,
                        str(PARTIE_2 / "meowdoku.py"),
                        str(GRILLE_SUJET),
                        str(output),
                        "--model",
                        representation,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(declaration, output.read_text(encoding="utf-8"))

    def test_cli_resout_et_confirme_la_verification_independante(self) -> None:
        for representation in ("positions", "cells"):
            with self.subTest(model=representation):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(PARTIE_2 / "solve_meowdoku.py"),
                        str(GRILLE_SUJET),
                        "--model",
                        representation,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.startswith("s SATISFIABLE\n"))
                self.assertIn("c solution vérifiée indépendamment", result.stdout)

    def test_cli_de_resolution_signale_les_grilles_invalides_sans_traceback(self) -> None:
        cases = [
            ("GRID 2 3\nZONES A B\nA A B\nA B B\n", "N = M = K"),
            ("GRID 2 2\nZONES A B\nA B\n", "2 lignes de 2 cases"),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected), TemporaryDirectory() as directory:
                path = Path(directory) / "grid.txt"
                path.write_text(text, encoding="utf-8")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(PARTIE_2 / "solve_meowdoku.py"),
                        str(path),
                        "--model",
                        "cells",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
