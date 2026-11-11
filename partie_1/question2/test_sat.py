"""Validation de la question 2 : python3 -m unittest -v."""

from itertools import product
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

if __package__:
    from .sat import dpll, dpll_valuation, lire_dimacs, simplifier, verifier_valuation
else:
    from sat import dpll, dpll_valuation, lire_dimacs, simplifier, verifier_valuation


RACINE = Path(__file__).resolve().parent.parent


def satisfiable_exhaustif(formule, n):
    """Oracle indépendant : essaie les 2**n valuations possibles."""
    return any(
        all(any(valeurs[abs(l) - 1] == (l > 0) for l in c) for c in formule)
        for valeurs in product((False, True), repeat=n)
    )


class TestsDPLL(unittest.TestCase):
    def verifier_solveurs(self, formule, attendu, seed=0):
        copie = [frozenset(c) for c in formule]
        self.assertEqual(dpll(formule, seed), attendu)
        statut, valuation = dpll_valuation(formule, seed)
        self.assertEqual(statut, attendu)
        if statut:
            self.assertTrue(verifier_valuation(formule, valuation))
        else:
            self.assertIsNone(valuation)
        self.assertEqual(formule, copie, "Le solveur ne doit pas modifier l'entrée.")

    def test_cas_elementaires(self):
        for clauses, attendu in [
            ([], True), ([[]], False), ([[1], [-1]], False),
            ([[1, 2], [-1, 2]], True),  # Littéral pur 2.
            ([[1, -1]], True),  # Tautologie.
            ([[1], [-1, 2], [-2, 3], [-3]], False),
            ([[1, 2], [-1, 2], [1, -2], [-1, -2]], False),
            ([[1, 2, 3], [-1, -2], [-2, -3], [2, 3]], True),  # Lampes du sujet.
        ]:
            with self.subTest(clauses=clauses):
                self.verifier_solveurs([frozenset(c) for c in clauses], attendu)

    def test_retour_arriere(self):
        # Aucun littéral pur/unitaire initial ; x1=False échoue, x1=True réussit.
        formule = [frozenset(c) for c in ([1, 2], [1, -2], [-1, 2])]
        for seed in range(20):
            self.verifier_solveurs(formule, True, seed)

    def test_simplification(self):
        formule = [frozenset(c) for c in ([1, 2], [-1, 3], [-1])]
        self.assertEqual(simplifier(formule, 1), [frozenset([3]), frozenset()])

    def test_toutes_les_formules_sur_deux_variables(self):
        # 9 clauses sans tautologie (dont la clause vide), donc 512 formules.
        clauses = [
            frozenset(p * signe for p, signe in enumerate(signes, 1) if signe)
            for signes in product((-1, 0, 1), repeat=2)
        ]
        for masque in range(1 << len(clauses)):
            formule = [c for i, c in enumerate(clauses) if masque & (1 << i)]
            with self.subTest(masque=masque):
                self.verifier_solveurs(formule, satisfiable_exhaustif(formule, 2))

    def test_formules_aleatoires(self):
        aleatoire = random.Random(2026)
        for numero in range(300):
            n = aleatoire.randint(1, 6)
            formule = [
                frozenset(aleatoire.choice((-1, 1)) * aleatoire.randint(1, n)
                          for _ in range(aleatoire.randint(1, 4)))
                for _ in range(aleatoire.randint(0, 20))
            ]
            with self.subTest(numero=numero):
                self.verifier_solveurs(formule, satisfiable_exhaustif(formule, n), numero)

    def test_grille(self):
        n, formule = lire_dimacs(RACINE / "instances/grille.cnf")
        self.assertEqual((n, len(formule)), (36, 408))
        for seed in range(20):
            self.verifier_solveurs(formule, True, seed)
        # Contrôle indépendant des contraintes du jeu sur le modèle obtenu.
        from question1.conversion import lire_grille
        grille = lire_grille(RACINE / "grilles/grille.txt")
        _, valuation = dpll_valuation(formule, seed=0)
        chats = [divmod(p - 1, 6) for p, valeur in valuation.items() if valeur]
        self.assertEqual(len(chats), 6)
        self.assertEqual(len({i for i, j in chats}), 6)
        self.assertEqual(len({j for i, j in chats}), 6)
        self.assertEqual({grille[i][j] for i, j in chats}, set("ABCDEF"))
        for k, (i, j) in enumerate(chats):
            for ni, nj in chats[k + 1:]:
                self.assertGreater(max(abs(i - ni), abs(j - nj)), 1)


class TestsDimacsEtCLI(unittest.TestCase):
    def lire_texte(self, texte):
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "test.cnf"
            chemin.write_text(texte, encoding="utf-8")
            return lire_dimacs(chemin)

    def test_dimacs(self):
        self.assertEqual(
            self.lire_texte("c exemple\n\np cnf 3 3\n1 1\nc suite\n-2 0 3 0\n0\n"),
            (3, [frozenset([1, -2]), frozenset([3]), frozenset()]),
        )
        self.assertEqual(self.lire_texte("p cnf 0 0\n"), (0, []))

    def test_dimacs_invalide(self):
        for texte in (
            "", "1 0\n", "p cnf 1 1\n2 0\n", "p cnf 1 1\n1\n",
            "p cnf 1 2\n1 0\n", "p cnf -1 0\n", "p cnf 1 0\np cnf 1 0\n",
            "p cnf 1 1\nx 0\n", "p autre 1 0\n",
        ):
            with self.subTest(texte=texte), self.assertRaises(ValueError):
                self.lire_texte(texte)

    def test_cli(self):
        resultat = subprocess.run(
            [sys.executable, str(RACINE / "question2/sat.py"), str(RACINE / "instances/grille.cnf"),
             "--mode", "dpll", "--seed", "0", "--output-model", "--stats"],
            capture_output=True, text=True, check=True,
        )
        lignes = resultat.stdout.splitlines()
        self.assertEqual(lignes[0], "s SATISFIABLE")
        self.assertEqual(len(lignes), 2)
        mots = lignes[1].split()
        self.assertEqual((mots[0], mots[-1]), ("v", "0"))
        litteraux = list(map(int, mots[1:-1]))
        self.assertEqual([abs(l) for l in litteraux], list(range(1, 37)))
        _, formule = lire_dimacs(RACINE / "instances/grille.cnf")
        self.assertTrue(verifier_valuation(formule, {abs(l): l > 0 for l in litteraux}))
        self.assertIn("Temps CPU", resultat.stderr)

    def test_cli_unsat_et_version_1(self):
        with TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "insatisfiable.cnf"
            chemin.write_text("p cnf 1 2\n1 0\n-1 0\n", encoding="utf-8")
            for options in (["--version", "1"], ["--output-model"]):
                resultat = subprocess.run(
                    [sys.executable, str(RACINE / "question2/sat.py"), str(chemin), *options],
                    capture_output=True, text=True, check=True,
                )
                self.assertEqual(resultat.stdout, "s UNSATISFIABLE\n")
                self.assertEqual(resultat.stderr, "")


if __name__ == "__main__":
    unittest.main()
