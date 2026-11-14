"""Question 4 : tests de la traduction en FNC.

1. mise en FNC (cnf.py) : clauses produites sans auxiliaire quand c'est
   possible, et équivalence de satisfiabilité vérifiée exhaustivement ;
2. encodage direct des domaines et clauses exactes des comparaisons ;
3. compteur séquentiel de Sinz : taille et sens ;
4. équivalence de bout en bout : pour chaque valeur possible des variables
   d'un petit modèle, la FNC (avec ces valeurs imposées) est satisfiable si et
   seulement si le modèle source est vrai, avec les deux encodages de
   atMostOne ;
5. les quatre modèles du sujet ont le statut attendu et leurs modèles SAT
   sont décodés ; les solutions des reines, de la coloration et du Sudoku
   sont en outre vérifiées selon leurs règles métier.
"""

from itertools import combinations, product
from pathlib import Path
import random
import sys
import unittest

from cnf import PAnd, PIff, PNot, POr, land, liff, lnot, lor, to_clauses
from encoding import decode, encode, sinz
from expansion import Cell, expand
from semantics import BOOL, analyse, cells
from syntax import parse
from tests.test_semantics import SourceInterpreter


PART_2 = Path(__file__).resolve().parent.parent
PART_1 = PART_2.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question2.sat import dpll_valuation, verifier_valuation  # noqa: E402


EXEMPLES = PART_2 / "exemples"


def satisfiable(clauses: list[list[int]], units: list[int] = ()) -> bool:
    formula = [frozenset(c) for c in clauses] + [frozenset([u]) for u in units]
    return dpll_valuation(formula, seed=0)[0]


def compile_text(text: str, amo: str = "pairwise"):
    model = analyse(parse(text))
    return model, encode(model, expand(model), amo)


def truth(formula, values: dict[int, bool]) -> bool:
    """Valeur d'une formule propositionnelle de cnf.py."""
    if isinstance(formula, bool):
        return formula
    if isinstance(formula, int):
        return values[abs(formula)] == (formula > 0)
    if isinstance(formula, PNot):
        return not truth(formula.item, values)
    if isinstance(formula, PIff):
        return truth(formula.left, values) == truth(formula.right, values)
    results = [truth(item, values) for item in formula.items]
    return all(results) if isinstance(formula, PAnd) else any(results)


class TestsMiseEnFNC(unittest.TestCase):
    def fresh_from(self, start: int):
        counter = [start]

        def fresh() -> int:
            counter[0] += 1
            return counter[0]
        return fresh

    def test_pas_d_auxiliaire_pour_les_clauses(self):
        fresh = self.fresh_from(3)
        cases = [
            (lor([1, 2, -3]), [[1, 2, -3]]),
            (land([1, lor([-2, 3])]), [[1], [-2, 3]]),
            (lor([lnot(1), 2]), [[-1, 2]]),                    # 1 -> 2
            (lnot(land([1, 2])), [[-1, -2]]),                  # not (1 and 2)
            (True, []),
            (False, [[]]),
        ]
        for formula, clauses in cases:
            with self.subTest(formula=formula):
                self.assertEqual(to_clauses(formula, fresh), clauses)

    def test_une_auxiliaire_par_conjonction_sous_une_disjonction(self):
        # 1 or (2 and 3) : t -> (2 and 3), puis la clause 1 or t
        self.assertEqual(
            to_clauses(lor([1, land([2, 3])]), self.fresh_from(3)),
            [[-4, 2], [-4, 3], [1, 4]],
        )

    def test_simplification_des_constantes(self):
        self.assertIs(land([1, False]), False)
        self.assertEqual(lor([False, 2]), 2)
        self.assertEqual(lnot(lnot(PAnd((1, 2)))), PAnd((1, 2)))
        self.assertEqual(liff(1, True), 1)
        self.assertEqual(liff(1, False), -1)

    def test_equisatisfiabilite_sur_des_formules_aleatoires(self):
        rng = random.Random(4)

        def random_formula(depth: int):
            if depth == 0 or rng.random() < 0.3:
                return rng.choice([1, 2, 3]) * rng.choice([1, -1])
            kind = rng.choice(["and", "or", "not", "iff"])
            if kind == "not":
                return lnot(random_formula(depth - 1))
            if kind == "iff":
                return liff(random_formula(depth - 1), random_formula(depth - 1))
            items = [random_formula(depth - 1) for _ in range(rng.randint(2, 3))]
            return land(items) if kind == "and" else lor(items)

        for number in range(300):
            formula = random_formula(4)
            clauses = to_clauses(formula, self.fresh_from(3))
            for values in product((False, True), repeat=3):
                assignment = dict(zip((1, 2, 3), values))
                units = [v if assignment[v] else -v for v in (1, 2, 3)]
                with self.subTest(number=number, values=values):
                    self.assertEqual(truth(formula, assignment), satisfiable(clauses, units))


class TestsEncodageDirect(unittest.TestCase):
    def test_domaine_1_a_3_comme_dans_le_sujet(self):
        _, encoding = compile_text("var x : 1..3;")
        self.assertEqual(encoding.cells[Cell("x")], {1: 1, 2: 2, 3: 3})
        self.assertEqual(encoding.clauses, [[1, 2, 3], [-1, -2], [-1, -3], [-2, -3]])
        self.assertEqual(encoding.id_to_name, {1: "x=1", 2: "x=2", 3: "x=3"})

    def test_un_booleen_reste_une_variable(self):
        _, encoding = compile_text("var b : bool; array e[2] : bool; constraint b;")
        self.assertEqual(encoding.id_to_name, {1: "b", 2: "e[1]", 3: "e[2]"})
        self.assertEqual(encoding.clauses, [[1]])

    def test_clauses_des_comparaisons(self):
        declarations = "var x : 1..3; var y : 1..3; "
        domain = [[1, 2, 3], [-1, -2], [-1, -3], [-2, -3],
                  [4, 5, 6], [-4, -5], [-4, -6], [-5, -6]]
        cases = [
            ("x = 2", [[2]]),
            ("x != 2", [[-2]]),
            ("x <= 1", [[1]]),               # une bonne valeur : x1
            ("x <= 2", [[-3]]),              # une mauvaise valeur : not x3
            ("x > 5", [[]]),                 # aucune valeur : clause vide
            ("x != y", [[-1, -4], [-2, -5], [-3, -6]]),
            ("x = y", [[-1, 4], [-2, 5], [-3, 6]]),
            ("x < y", [[-1, 5, 6], [-2, 6], [-3]]),
            ("x <= y", [[-1, 4, 5, 6], [-2, 5, 6], [-3, 6]]),
        ]
        for constraint, clauses in cases:
            with self.subTest(constraint=constraint):
                _, encoding = compile_text(f"{declarations} constraint {constraint};")
                self.assertEqual(encoding.clauses, domain + clauses)

    def test_valeurs_enumerees(self):
        _, encoding = compile_text(
            "enum C = { R, G, B }; var c : C; constraint c > R;"
        )
        self.assertEqual(encoding.clauses[-1], [-1])        # not c=R
        self.assertEqual(encoding.id_to_name[1], "c=R")


class TestsSinz(unittest.TestCase):
    def test_taille_3n_moins_4(self):
        for n in range(2, 9):
            counter = [n]

            def fresh() -> int:
                counter[0] += 1
                return counter[0]
            clauses = sinz(list(range(1, n + 1)), fresh)
            self.assertEqual(len(clauses), 3 * n - 4)
            self.assertEqual(counter[0] - n, n - 1)

    def test_sens_au_plus_un(self):
        n = 5
        counter = [n]

        def fresh() -> int:
            counter[0] += 1
            return counter[0]
        clauses = sinz(list(range(1, n + 1)), fresh)
        for values in product((False, True), repeat=n):
            units = [i + 1 if v else -(i + 1) for i, v in enumerate(values)]
            self.assertEqual(satisfiable(clauses, units), sum(values) <= 1)

    def test_comparaison_avec_l_encodage_deux_a_deux(self):
        text = "array b[10] : bool; constraint atMostOne(b[*]);"
        _, pairwise = compile_text(text, "pairwise")
        _, counter = compile_text(text, "sinz")
        self.assertEqual(len(pairwise.clauses), 45)          # 10 * 9 / 2
        self.assertEqual(len(counter.clauses), 26)           # 3 * 10 - 4
        self.assertEqual(counter.variable_count - pairwise.variable_count, 9)


class TestsEquivalence(unittest.TestCase):
    MODELS = [
        "var x : 1..3; var y : 2..4;\n"
        "constraint x < y or x = 3;\n"
        "constraint not (y <= x) -> x != 2;\n"
        "constraint x >= 2 or y > 3;",

        "enum C = { R, G, B }; array c[2] : C;\n"
        "constraint c[1] <= c[2];\n"
        "constraint c[2] != B or c[1] = R;",

        "array b[3] : bool; var p : bool;\n"
        "constraint p -> not atMostOne(b[*]);\n"
        "constraint not p -> exactlyOne(b[*]);\n"
        "constraint atLeastOne(b[1], p);",

        "array b[4] : bool;\n"
        "constraint atMostOne(b[*]);\n"
        "constraint exactlyOne(b[2], b[3], b[4]);",

        "array v[3] : 1..3; var w : 2..4;\n"
        "constraint allDifferent(v[*], w);\n"
        "constraint (v[1] = 1) = (w = 2);",

        "array v[2] : 1..3;\n"
        "constraint not allDifferent(v[*], 2);",

        "var p : bool; var q : bool;\n"
        "constraint (p = q) != (not p);",
    ]

    # Une seule comparaison par modèle : une erreur sur un opérateur ne peut
    # pas être masquée par une autre contrainte.
    for op in ("=", "!=", "<", "<=", ">", ">="):
        MODELS += [
            f"var x : 1..3; var y : 2..4; constraint x {op} y;",
            f"var x : 1..3; constraint x {op} 2;",
            f"var x : 1..3; constraint 2 {op} x;",
            f"var x : 1..3; constraint not x {op} 2;",
            f"enum C = {{ R, G, B }}; var c : C; var d : C; constraint c {op} d;",
            f"enum C = {{ R, G, B }}; var c : C; constraint c {op} G;",
        ]
    del op

    def test_memes_solutions_que_le_modele_source(self):
        for amo in ("pairwise", "sinz"):
            for text in self.MODELS:
                with self.subTest(amo=amo, model=text):
                    model, encoding = compile_text(text, amo)
                    all_cells = [(Cell(v.name, key), v) for v in model.variables
                                 for key in cells(v)]
                    solutions = 0
                    for values in product(*(v.domain.values for _, v in all_cells)):
                        assignment = {cell: value for (cell, _), value in zip(all_cells, values)}
                        units = []
                        for cell, value in assignment.items():
                            ids = encoding.cells[cell]
                            if encoding.domains[cell].type == BOOL:
                                units.append(ids[True] if value else -ids[True])
                            else:
                                units.extend(i if v == value else -i for v, i in ids.items())
                        source = all(SourceInterpreter(model, assignment).statement(s, {})
                                     for s in model.statements)
                        self.assertEqual(satisfiable(encoding.clauses, units), source, assignment)
                        solutions += source
                    self.assertGreater(solutions, 0)


class TestsModelesDuSujet(unittest.TestCase):
    EXPECTED = {"pigeonhole.csp": False, "queens.csp": True,
                "coloring.csp": True, "sudoku.csp": True}

    PETERSEN_EDGES = (
        (1, 2), (2, 3), (3, 4), (4, 5), (5, 1),
        (6, 8), (8, 10), (10, 7), (7, 9), (9, 6),
        (1, 6), (2, 7), (3, 8), (4, 9), (5, 10),
    )

    SUDOKU_GIVENS = (
        (5, 3, 0, 0, 7, 0, 0, 0, 0),
        (6, 0, 0, 1, 9, 5, 0, 0, 0),
        (0, 9, 8, 0, 0, 0, 0, 6, 0),
        (8, 0, 0, 0, 6, 0, 0, 0, 3),
        (4, 0, 0, 8, 0, 3, 0, 0, 1),
        (7, 0, 0, 0, 2, 0, 0, 0, 6),
        (0, 6, 0, 0, 0, 0, 2, 8, 0),
        (0, 0, 0, 4, 1, 9, 0, 0, 5),
        (0, 0, 0, 0, 8, 0, 0, 7, 9),
    )

    def assert_coloring_solution(self, values):
        colors = {
            cell.indices[0]: value.name
            for cell, value in values.items()
            if cell.name == "color"
        }
        self.assertEqual(set(colors), set(range(1, 11)))
        self.assertLessEqual(set(colors.values()), {"Red", "Green", "Blue"})
        for left, right in self.PETERSEN_EDGES:
            self.assertNotEqual(colors[left], colors[right], (left, right))
        self.assertEqual(colors[1], "Red")
        self.assertEqual(colors[2], "Green")

    def assert_sudoku_solution(self, values):
        grid = {
            cell.indices: value
            for cell, value in values.items()
            if cell.name == "grid"
        }
        indices = range(1, 10)
        expected_cells = {(row, column) for row in indices for column in indices}
        digits = set(indices)
        self.assertEqual(set(grid), expected_cells)
        self.assertTrue(all(value in digits for value in grid.values()))

        for index in indices:
            self.assertEqual({grid[index, column] for column in indices}, digits)
            self.assertEqual({grid[row, index] for row in indices}, digits)

        for first_row in (1, 4, 7):
            for first_column in (1, 4, 7):
                block = {
                    grid[row, column]
                    for row in range(first_row, first_row + 3)
                    for column in range(first_column, first_column + 3)
                }
                self.assertEqual(block, digits)

        for row, givens in enumerate(self.SUDOKU_GIVENS, start=1):
            for column, given in enumerate(givens, start=1):
                if given:
                    self.assertEqual(grid[row, column], given, (row, column))

    def test_statuts_attendus_et_modeles_decodes(self):
        for amo in ("pairwise", "sinz"):
            for name, expected in self.EXPECTED.items():
                with self.subTest(amo=amo, model=name):
                    model, encoding = compile_text(
                        (EXEMPLES / name).read_text(encoding="utf-8"), amo
                    )
                    formula = [frozenset(c) for c in encoding.clauses]
                    status, valuation = dpll_valuation(formula, seed=0)
                    self.assertEqual(status, expected)
                    if status:
                        self.assertTrue(verifier_valuation(formula, valuation))
                        values = decode(encoding, valuation)
                        self.assertEqual(len(values), len(encoding.cells))
                        if name == "coloring.csp":
                            self.assert_coloring_solution(values)
                        elif name == "sudoku.csp":
                            self.assert_sudoku_solution(values)

    def test_huit_reines_sans_conflit(self):
        model, encoding = compile_text((EXEMPLES / "queens.csp").read_text(encoding="utf-8"))
        status, valuation = dpll_valuation([frozenset(c) for c in encoding.clauses], seed=0)
        queen = {cell.indices[0]: value for cell, value in decode(encoding, valuation).items()}
        for i, j in combinations(range(1, 9), 2):
            self.assertNotEqual(queen[i], queen[j])
            self.assertNotEqual(abs(queen[i] - queen[j]), j - i)


if __name__ == "__main__":
    unittest.main()
