"""Tests du protocole experimental de la question 6.3."""

from pathlib import Path
import sys
import unittest

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_Q63 = RACINE / "partie_2/question6.3"
if str(DOSSIER_Q63) not in sys.path:
    sys.path.insert(0, str(DOSSIER_Q63))

from benchmark_q63 import mesurer_modele, profil_clauses, resumer  # noqa: E402


GRILLE_6 = RACINE / "partie_1/grilles/q5/meow_sat_06_s1.txt"


class TestsBenchmarkQ63(unittest.TestCase):
    def test_profil_des_clauses(self) -> None:
        self.assertEqual(
            profil_clauses([[1], [-1, 2], [1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4, 5]]),
            {
                "clauses_unitaires": 1,
                "clauses_binaires": 1,
                "clauses_ternaires": 1,
                "clauses_longues": 2,
                "occurrences_litteraux": 15,
            },
        )

    def test_les_deux_modeles_sont_mesures_et_verifies(self) -> None:
        resultats = {}
        for modele in ("positions", "cells"):
            lignes = mesurer_modele(
                GRILLE_6,
                modele,
                repetitions=1,
                repetitions_compilation=1,
                limite_s=5,
            )
            self.assertEqual(len(lignes), 1)
            ligne = lignes[0]
            self.assertEqual(ligne["statut"], "SAT")
            self.assertEqual(ligne["modele"], modele)
            self.assertGreater(ligne["variables"], 0)
            self.assertGreater(ligne["clauses"], 0)
            resultats[modele] = ligne

        # Invariant structurel de ces deux formulations, independant du temps.
        self.assertGreater(
            resultats["positions"]["variables"], resultats["cells"]["variables"]
        )
        self.assertGreater(
            resultats["positions"]["clauses"], resultats["cells"]["clauses"]
        )

    def test_resume_signale_les_timeouts_et_calcule_les_ratios(self) -> None:
        base = {
            "taille": "6",
            "instance": "g.txt",
            "compilation_cpu_ms": "10",
            "variables": "20",
            "clauses_binaires": "80",
            "retours_arriere": "2",
            "propagations_unitaires": "30",
        }
        lignes = [
            {
                **base,
                "modele": "positions",
                "statut": "SAT",
                "clauses": "200",
                "resolution_cpu_ms": "12",
                "decisions": "10",
            },
            {
                **base,
                "modele": "positions",
                "statut": "TIMEOUT",
                "clauses": "200",
                "resolution_cpu_ms": "30",
                "decisions": "99",
            },
            {
                **base,
                "modele": "cells",
                "statut": "SAT",
                "clauses": "100",
                "resolution_cpu_ms": "4",
                "decisions": "5",
            },
        ]
        rapport = resumer(lignes)
        self.assertIn("1/2", rapport)
        self.assertIn("| 6 | 2.00x | - | - |", rapport)
        self.assertIn("ne sont pas calculés", rapport)


if __name__ == "__main__":
    unittest.main()
