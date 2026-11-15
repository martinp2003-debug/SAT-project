"""Tests du protocole expérimental de la question 6.4."""

from pathlib import Path
import sys
import unittest


RACINE = Path(__file__).resolve().parents[2]
DOSSIER_Q64 = RACINE / "partie_2/question6.4"
if str(DOSSIER_Q64) not in sys.path:
    sys.path.insert(0, str(DOSSIER_Q64))

from benchmark_q64 import mesurer_variante, resumer  # noqa: E402


GRILLE_6 = RACINE / "partie_1/grilles/q5/meow_sat_06_s1.txt"


class TestsBenchmarkQ64(unittest.TestCase):
    def test_les_deux_variantes_sont_mesurees_et_verifiees(self) -> None:
        resultats = {}
        for redundant_regions in (False, True):
            lignes = mesurer_variante(
                GRILLE_6,
                redundant_regions,
                repetitions=1,
                repetitions_compilation=1,
                limite_s=5,
            )
            self.assertEqual(len(lignes), 1)
            ligne = lignes[0]
            self.assertEqual(ligne["statut"], "SAT")
            resultats[ligne["variante"]] = ligne

        sans, avec = resultats["sans"], resultats["avec"]
        self.assertEqual(sans["variables"], avec["variables"])
        self.assertEqual(avec["clauses"] - sans["clauses"], 6)

    def test_resume_calcule_les_deltas_et_gains(self) -> None:
        base = {
            "taille": "6",
            "instance": "g.txt",
            "statut": "SAT",
            "compilation_cpu_ms": "10",
            "variables": "36",
            "clauses_longues": "5",
            "retours_arriere": "4",
            "propagations_unitaires": "30",
        }
        lignes = [
            {
                **base,
                "variante": "sans",
                "clauses": "100",
                "resolution_cpu_ms": "12",
                "decisions": "10",
            },
            {
                **base,
                "variante": "avec",
                "clauses": "106",
                "resolution_cpu_ms": "6",
                "decisions": "5",
                "retours_arriere": "2",
            },
        ]
        rapport = resumer(lignes)
        self.assertIn("| 6 | 0 | 6 | 2.00x | 2.00x | 2.00x |", rapport)
        self.assertIn("principe des tiroirs", rapport)

    def test_resume_ne_compare_pas_une_variante_en_timeout(self) -> None:
        base = {
            "taille": "6",
            "instance": "g.txt",
            "compilation_cpu_ms": "10",
            "variables": "36",
            "clauses_longues": "5",
            "retours_arriere": "4",
            "propagations_unitaires": "30",
            "decisions": "10",
        }
        lignes = [
            {
                **base,
                "variante": "sans",
                "statut": "TIMEOUT",
                "clauses": "100",
                "resolution_cpu_ms": "30",
            },
            {
                **base,
                "variante": "avec",
                "statut": "SAT",
                "clauses": "106",
                "resolution_cpu_ms": "6",
            },
        ]
        rapport = resumer(lignes)
        self.assertIn("| 6 | 0 | 6 | - | - | - |", rapport)
        self.assertIn("timeout", rapport)


if __name__ == "__main__":
    unittest.main()
