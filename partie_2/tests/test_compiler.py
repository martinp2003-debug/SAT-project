"""Question 1 : tests de la chaîne AST -> FNC -> DIMACS -> DPLL.

Le fichier suit le même ordre que la chaîne de compilation :

1. construire et valider la table des symboles ;
2. encoder les expressions avec la transformation de Tseitin ;
3. sérialiser la FNC en DIMACS ;
4. résoudre puis traduire le modèle dans les noms du fichier source.

Les tests de clauses exactes expliquent localement l'encodage. Le test
exhaustif vérifie ensuite sa propriété essentielle sans dépendre des clauses
attendues : une expression et sa FNC ont les mêmes valuations possibles sur
les variables nommées.
"""

from itertools import product
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from compiler import CompilationError, compile_program
from dimacs import to_dimacs, write_dimacs
from evaluation import evaluate_expression, evaluate_program
from syntax import (
    And,
    Constraint,
    EnumDomain,
    Implies,
    Not,
    Or,
    Program,
    Var,
    VarDecl,
    parse,
)


PART_2 = Path(__file__).resolve().parent.parent
PART_1 = PART_2.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question2.sat import dpll_valuation, lire_dimacs  # noqa: E402


def cnf_is_true(clauses: list[list[int]], valuation: dict[int, bool]) -> bool:
    """Évalue directement une FNC sous une valuation totale DIMACS."""
    return all(
        any(valuation[abs(literal)] == (literal > 0) for literal in clause)
        for clause in clauses
    )


class TestsTableDesSymboles(unittest.TestCase):
    """Première passe : associer un identifiant stable à chaque déclaration."""

    def test_les_identifiants_suivent_l_ordre_des_declarations(self):
        result = compile_program(parse("var y : bool; var x : bool; constraint x;"))
        self.assertEqual(result.name_to_id, {"y": 1, "x": 2})
        self.assertEqual(result.id_to_name, {1: "y", 2: "x"})

    def test_une_declaration_double_est_rejetee(self):
        with self.assertRaisesRegex(CompilationError, "déclaration en double : x"):
            compile_program(parse("var x : bool; var x : bool;"))

    def test_une_variable_inconnue_est_rejetee(self):
        with self.assertRaisesRegex(CompilationError, "variable non déclarée : y"):
            compile_program(parse("var x : bool; constraint y;"))


class TestsEncodageTseitin(unittest.TestCase):
    """Deuxième passe : encoder chaque type de nœud de l'AST en clauses."""

    def test_clauses_exactes_pour_chaque_type_de_noeud(self):
        # x et not x sont déjà des littéraux : aucune auxiliaire n'est créée.
        # Les connecteurs binaires utilisent la variable auxiliaire 3 puis la
        # dernière clause [3] impose la racine de la contrainte à vrai.
        cases = [
            ("constraint x;", 2, [[1]]),
            ("constraint not x;", 2, [[-1]]),
            (
                "constraint x and y;",
                3,
                [[-3, 1], [-3, 2], [3, -1, -2], [3]],
            ),
            (
                "constraint x or y;",
                3,
                [[3, -1], [3, -2], [-3, 1, 2], [3]],
            ),
            (
                "constraint x -> y;",
                3,
                [[3, 1], [3, -2], [-3, -1, 2], [3]],
            ),
        ]
        declarations = "var x : bool; var y : bool; "
        for constraint, expected_count, expected_clauses in cases:
            with self.subTest(constraint=constraint):
                result = compile_program(parse(declarations + constraint))
                self.assertEqual(result.variable_count, expected_count)
                self.assertEqual(result.clauses, expected_clauses)

    def test_plusieurs_contraintes_sont_conjointes(self):
        result = compile_program(
            parse("var x : bool; constraint x; constraint not x;")
        )
        self.assertEqual(result.clauses, [[1], [-1]])
        self.assertFalse(
            dpll_valuation([frozenset(c) for c in result.clauses])[0]
        )

    def test_equivalence_de_tseitin_par_enumeration_exhaustive(self):
        # On engendre 114 expressions de profondeur au plus deux. Pour chaque
        # valuation de x et y, on essaie toutes les valuations des auxiliaires.
        # Il doit exister une extension satisfaisant la FNC si et seulement si
        # l'expression source est vraie.
        x, y = Var("x"), Var("y")
        level_one = [x, y, Not(x), And(x, y), Or(x, y), Implies(x, y)]
        expressions = level_one + [
            constructor(left, right)
            for constructor in (And, Or, Implies)
            for left in level_one
            for right in level_one
        ]

        for expression in expressions:
            program = Program(
                [
                    VarDecl("x", EnumDomain("bool")),
                    VarDecl("y", EnumDomain("bool")),
                    Constraint(expression),
                ]
            )
            result = compile_program(program)
            with self.subTest(expression=expression):
                source_is_satisfiable = False
                for x_value, y_value in product((False, True), repeat=2):
                    source_valuation = {"x": x_value, "y": y_value}
                    source_result = evaluate_expression(expression, source_valuation)
                    source_is_satisfiable |= source_result
                    extension_exists = False
                    auxiliary_count = result.variable_count - 2
                    for auxiliary_values in product(
                        (False, True), repeat=auxiliary_count
                    ):
                        sat_valuation = {1: x_value, 2: y_value}
                        sat_valuation.update(
                            {
                                identifier: value
                                for identifier, value in enumerate(
                                    auxiliary_values, start=3
                                )
                            }
                        )
                        if cnf_is_true(result.clauses, sat_valuation):
                            extension_exists = True
                            self.assertTrue(source_result)
                    self.assertEqual(extension_exists, source_result)

                satisfiable, valuation = dpll_valuation(
                    [frozenset(clause) for clause in result.clauses], seed=0
                )
                self.assertEqual(satisfiable, source_is_satisfiable)
                if satisfiable:
                    self.assertIsNotNone(valuation)
                    named = {
                        name: (valuation or {}).get(identifier, False)
                        for name, identifier in result.name_to_id.items()
                    }
                    self.assertTrue(evaluate_program(program, named))
                else:
                    self.assertIsNone(valuation)


class TestsFormatDimacs(unittest.TestCase):
    """Troisième passe : produire un fichier lisible par la partie I."""

    def test_la_correspondance_est_stable_et_la_fnc_est_relisible(self):
        result = compile_program(
            parse("var x : bool; var y : bool; constraint x or y;")
        )
        text = to_dimacs(result)
        self.assertTrue(text.startswith("c var 1 x\nc var 2 y\np cnf 3 4\n"))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "formula.cnf"
            write_dimacs(path, result)
            variable_count, clauses = lire_dimacs(path)
        self.assertEqual(variable_count, result.variable_count)
        self.assertEqual(clauses, [frozenset(c) for c in result.clauses])


class TestsChaineComplete(unittest.TestCase):
    """Quatrième passe : tester l'interface utilisateur de bout en bout."""

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Exécute la vraie CLI et capture son code, stdout et stderr."""
        return subprocess.run(
            [sys.executable, "csp.py", *arguments],
            cwd=PART_2,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_le_modele_du_sujet_est_resolu_et_decode(self):
        result = self.run_cli("examples/subject.csp", "--solve")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("s SATISFIABLE", result.stdout)
        values = {
            name: value == "true"
            for name, value in (
                line.split(" = ") for line in result.stdout.splitlines()[1:]
            )
        }
        source = (PART_2 / "examples/subject.csp").read_text(encoding="utf-8")
        self.assertTrue(evaluate_program(parse(source), values))

    def test_sans_option_la_sortie_est_du_dimacs(self):
        result = self.run_cli("examples/subject.csp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("c var 1 x\n", result.stdout)
        # La CLI utilise l'encodage de la question 4 : ces trois contraintes
        # sont déjà des clauses, aucune variable auxiliaire n'est créée.
        self.assertIn("p cnf 3 4\n", result.stdout)
        self.assertNotIn("Program", result.stdout)

    def test_un_modele_contradictoire_est_insatisfiable(self):
        with TemporaryDirectory() as directory:
            model = Path(directory) / "unsat.csp"
            model.write_text(
                "var x : bool; constraint x; constraint not x;",
                encoding="utf-8",
            )
            result = self.run_cli(str(model), "--solve")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "s UNSATISFIABLE\n")

    def test_on_peut_ecrire_le_dimacs_et_resoudre_en_meme_temps(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "subject.cnf"
            result = self.run_cli(
                "examples/subject.csp", "--dimacs", str(output), "--solve"
            )
            variable_count, clauses = lire_dimacs(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(variable_count, 3)
        self.assertTrue(clauses)

    def test_les_erreurs_attendues_ne_produisent_pas_de_traceback(self):
        cases = [
            ("missing.csp", "No such file or directory"),
        ]
        with TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.csp"
            duplicate.write_text("var x : bool; var x : bool;", encoding="utf-8")
            unknown = Path(directory) / "unknown.csp"
            unknown.write_text("constraint x;", encoding="utf-8")
            syntax_error = Path(directory) / "syntax-error.csp"
            syntax_error.write_text("constraint x or;", encoding="utf-8")
            cases.extend(
                [
                    (str(duplicate), "déclaration en double : x"),
                    (str(unknown), "nom non déclaré : x"),
                    (str(syntax_error), "ligne 1, colonne 16 : « ; » inattendu"),
                ]
            )
            for model, message in cases:
                with self.subTest(model=model):
                    result = self.run_cli(model)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
