"""Question 3 : tests de l'analyse et de la transformation de l'arbre.

1. analyse : table des symboles, valeurs des constantes, domaines ;
2. erreurs : chaque erreur de la description du langage, avec sa position ;
3. déroulage : boucles, tranches, valeurs connues, court-circuit ;
4. simplifications et normalisation des comparaisons ;
5. équivalence : sur de petits modèles, la liste de contraintes obtenue a
   exactement les mêmes solutions que le modèle source, vérifié par
   énumération de toutes les valeurs des variables ;
6. les quatre modèles du sujet.
"""

from itertools import product
from pathlib import Path
import unittest

from diagnostics import CompilationError
from expansion import Cell, expand, show
from semantics import (
    ConstSymbol,
    EnumValue,
    VarSymbol,
    analyse,
    cells,
    compare_values,
    evaluate,
)
from syntax import (
    Access,
    And,
    Call,
    Compare,
    Constraint,
    Implies,
    Not,
    Or,
    Star,
    Var,
    parse,
)


EXEMPLES = Path(__file__).resolve().parent.parent / "exemples"


def expanded(text: str) -> list[str]:
    """Les contraintes déroulées d'un modèle, sous forme de texte."""
    return [show(c) for c in expand(analyse(parse(text))).constraints]


class TestsAnalyse(unittest.TestCase):
    def test_constantes_domaines_et_tableaux(self):
        model = analyse(parse(
            "const N = 2 * 3 - 1;\n"
            "enum Color = { Red, Green };\n"
            "const t[2][Color] = [[1, 2], [N, abs(-4)]];\n"
            "var x : N - 2..N;\n"
            "array used[Color] : bool;\n"
        ))
        self.assertEqual(model.symbols["N"].values[()], 5)
        red, green = EnumValue("Color", 0, "Red"), EnumValue("Color", 1, "Green")
        t = model.symbols["t"]
        self.assertIsInstance(t, ConstSymbol)
        self.assertEqual(t.values, {(1, red): 1, (1, green): 2, (2, red): 5, (2, green): 4})
        x, used = model.variables
        self.assertEqual(x.domain.values, (3, 4, 5))
        self.assertIsInstance(used, VarSymbol)
        self.assertEqual(cells(used), [(red,), (green,)])

    def test_les_valeurs_enumerees_sont_ordonnees(self):
        model = analyse(parse("enum C = { A, B, C2 }; const t[2] = [C2, A];"))
        values = model.symbols["t"].values
        self.assertTrue(compare_values("<", values[(2,)], values[(1,)]))
        self.assertEqual(evaluate(parse("constraint t[1] > B;").statements[0].expr,
                                  model.symbols, {}), True)


class TestsErreurs(unittest.TestCase):
    """Chaque modèle est rejeté avec un message et sa position."""

    def test_modeles_errones(self):
        cases = [
            ("constraint w;", "ligne 1, colonne 12 : nom non déclaré : w"),
            ("var x : bool; var x : 1..3;", "ligne 1, colonne 15 : déclaration en double : x"),
            ("enum C = { R }; var R : bool;", "déclaration en double : R"),
            ("const N = 2; forall N in 1..3 { }", "déclaration en double : N"),
            ("forall i in 1..2, i in 1..2 { }", "déclaration en double : i"),
            ("enum C = { R, G }; var c : C; constraint c = 1;", "comparaison entre C et entier"),
            ("var a : bool; constraint a + 1 = 2;", "l'arithmétique attend un entier, pas un booléen"),
            ("var x : 1..3; var y : 1..3; constraint x + 1 = y;",
             "l'arithmétique ne porte que sur des valeurs connues"),
            ("var a : bool; var b : bool; constraint a < b;", "'<' ne s'applique pas aux booléens"),
            ("var x : 1..3; constraint x;", "une contrainte attend un booléen, pas un entier"),
            ("var x : 1..3; constraint not x;", "'not' attend un booléen"),
            ("array g[3][3] : 1..3; constraint g[1] = 2;", "'g' attend 2 indice(s), 1 donné(s)"),
            ("var x : bool; constraint x[1];", "'x' n'est pas un tableau"),
            ("array g[3] : bool; constraint g;", "le tableau 'g' doit être indicé"),
            ("array g[3] : 1..3; var i : 1..3; constraint g[i] = 1;",
             "l'indice 1 de 'g' doit être une valeur connue à la compilation"),
            ("enum C = { R, G }; array u[C] : bool; constraint u[1];",
             "l'indice 1 de 'u' doit être un C, pas un entier"),
            ("array a[3] : 1..3; constraint a[4] = 1;",
             "ligne 1, colonne 31 : l'indice 1 de 'a' vaut 4, hors de 1..3"),
            ("array g[3] : 1..3; constraint g[*] = 1;",
             "une tranche n'est permise qu'en argument d'une contrainte globale"),
            ("var x : 1..3; constraint atMostOne(x);", "atMostOne attend des booléens, pas un entier"),
            ("var a : bool; constraint allDifferent(a);", "allDifferent porte sur des entiers"),
            ("enum C = { R }; var c : C; var x : 1..2; constraint allDifferent(c, x);",
             "allDifferent mélange C et entier"),
            ("constraint atLeastOne();", "atLeastOne attend au moins un argument"),
            ("var x : bool; constraint foo(x);", "fonction inconnue : foo"),
            ("var x : 1..3; constraint abs(x) = 1;", "l'argument de abs doit être une valeur connue"),
            ("enum C = { R }; constraint C = R;", "'C' est un type, pas une valeur"),
            ("var x : 3..1;", "domaine vide : 3..1"),
            ("var b : bool; var x : 1..b;", "une borne d'intervalle doit être une valeur connue"),
            ("array a[0] : bool;", "la taille d'un tableau doit être au moins 1, pas 0"),
            ("var x : Foo;", "nom non déclaré : Foo"),
            ("const N = 3; var x : N;", "'N' n'est pas un type énuméré"),
            ("const t[2] = [1, 2, 3];", "'t' : la dimension 1 doit contenir 2 élément(s)"),
            ("enum C = { R }; const t[2] = [1, R];", "'t' mélange des valeurs de types différents"),
        ]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaises(CompilationError) as error:
                    expand(analyse(parse(text)))
                self.assertIn(message, str(error.exception))


class TestsDeroulage(unittest.TestCase):
    def test_boucles_imbriquees_et_bornes_calculees(self):
        self.assertEqual(
            expanded(
                "const N = 3; array g[N][N] : 1..N;\n"
                "forall i in 1..N, j in i + 1..N { constraint g[i][j] != g[j][i]; }"
            ),
            ["g[1][2] != g[2][1]", "g[1][3] != g[3][1]", "g[2][3] != g[3][2]"],
        )

    def test_boucle_sur_un_type_enumere_et_intervalle_vide(self):
        self.assertEqual(
            expanded("enum C = { R, G }; array u[C] : bool;"
                     " forall c in C { constraint u[c]; }"),
            ["u[R]", "u[G]"],
        )
        # Une boucle vide n'évalue jamais son corps : g[3] n'est pas une erreur.
        self.assertEqual(
            expanded("array g[2] : bool; forall i in 3..2 { constraint g[i]; }"), []
        )

    def test_tranches_ligne_par_ligne(self):
        self.assertEqual(
            expanded("array g[2][2] : 1..2; constraint allDifferent(g[*][*]);"
                     " constraint allDifferent(g[*][2], g[1][1]);"),
            ["allDifferent(g[1][1], g[1][2], g[2][1], g[2][2])",
             "allDifferent(g[1][2], g[2][2], g[1][1])"],
        )

    def test_tranche_d_un_tableau_constant(self):
        self.assertEqual(
            expanded("const t[3] = [1, 2, 3]; var x : 1..4;"
                     " constraint allDifferent(t[*], x);"),
            ["allDifferent(1, 2, 3, x)"],
        )

    def test_tableau_constant_comme_indice(self):
        self.assertEqual(
            expanded("const e[1][2] = [[2, 1]]; array c[2] : 1..3;"
                     " forall k in 1..1 { constraint c[e[k][1]] != c[e[k][2]]; }"),
            ["c[2] != c[1]"],
        )

    def test_court_circuit_protege_un_acces_hors_bornes(self):
        text = ("const N = 3; array g[N] : 1..N;\n"
                "forall i in 1..N {{ constraint {}; }}")
        for guard in ("i < N -> g[i + 1] != g[i]",
                      "i = N or g[i + 1] != g[i]",
                      "i < N and g[i + 1] != g[i]",
                      "not (i < N) or g[i + 1] != g[i]"):
            with self.subTest(guard=guard):
                self.assertEqual(
                    expanded(text.format(guard))[:2], ["g[2] != g[1]", "g[3] != g[2]"]
                )
        # sans condition, g[4] est réellement évalué : c'est une erreur
        with self.assertRaisesRegex(CompilationError, "l'indice 1 de 'g' vaut 4"):
            expanded(text.format("g[i + 1] != g[i]"))
        # la condition est à droite : g[4] est évalué avant elle
        with self.assertRaisesRegex(CompilationError, "vaut 4"):
            expanded(text.format("g[i + 1] != g[i] or i = N"))


class TestsSimplifications(unittest.TestCase):
    def test_connecteurs_avec_un_operande_connu(self):
        cases = [
            ("1 < 2 and x", "x"),
            ("x and 2 < 1", "false"),
            ("1 < 2 or x", None),            # vraie : la contrainte disparaît
            ("x or 2 < 1", "x"),
            ("2 < 1 -> x", None),
            ("1 < 2 -> x", "x"),
            ("x -> 2 < 1", "not x"),
            ("x -> 1 < 2", None),
            ("not not x", "x"),
            ("atLeastOne(x, 1 < 2)", None),
            ("atLeastOne(x, 2 < 1)", "x"),
            ("atMostOne(x, y, 1 < 2)", "(not x and not y)"),
            ("atMostOne(x, 1 < 2, 1 < 2)", "false"),
            ("exactlyOne(x, y, 2 < 1)", "exactlyOne(x, y)"),
            ("exactlyOne(2 < 1)", "false"),
            ("allDifferent(n, 1, 2)", "allDifferent(n, 1, 2)"),
            ("allDifferent(n, 2, 2)", "false"),
            ("allDifferent(n)", None),
        ]
        for source, result in cases:
            with self.subTest(source=source):
                constraints = expanded(
                    f"var x : bool; var y : bool; var n : 1..3; constraint {source};"
                )
                self.assertEqual(constraints, [] if result is None else [result])

    def test_une_contrainte_fausse_donne_un_avertissement(self):
        expansion = expand(analyse(parse(
            "var x : bool;\nforall i in 1..2 { constraint i = 2 and x; }"
        )))
        self.assertEqual([show(c) for c in expansion.constraints], ["false", "x"])
        self.assertEqual(
            expansion.warnings,
            ["ligne 2, colonne 20 : contrainte toujours fausse (pour i = 1)"
             " : le modèle est insatisfiable"],
        )

    def test_normalisation_des_comparaisons(self):
        cases = [
            ("not x = 2", "x != 2"),
            ("not x < 2", "x >= 2"),
            ("3 < x", "x > 3"),
            ("3 = x", "x = 3"),
            ("x > y", "y < x"),
            ("x >= y", "y <= x"),
            ("not x < y", "y <= x"),
            ("not (x != y)", "x = y"),
            ("b = (1 < 2)", "b"),
            ("b != (1 < 2)", "not b"),
            ("(1 < 2) = b", "b"),
        ]
        for source, result in cases:
            with self.subTest(source=source):
                self.assertEqual(
                    expanded(f"var x : 1..3; var y : 1..3; var b : bool; constraint {source};"),
                    [result],
                )


# ------------------------------------------------------------
# Équivalence par énumération : un interpréteur indépendant du modèle
# source, écrit directement sur l'AST, sert d'oracle.
# ------------------------------------------------------------

def holds_globally(name: str, values: list) -> bool:
    if name == "allDifferent":
        keys = [v.index if isinstance(v, EnumValue) else v for v in values]
        return len(keys) == len(set(keys))
    count = sum(1 for v in values if v)
    return {"atLeastOne": count >= 1, "atMostOne": count <= 1,
            "exactlyOne": count == 1}[name]


class SourceInterpreter:
    """Valeur d'une expression source sous une valuation des cases."""

    def __init__(self, model, assignment: dict):
        self.model, self.assignment = model, assignment

    def value(self, expr, env: dict):
        symbols = self.model.symbols
        if isinstance(expr, Var) and isinstance(symbols.get(expr.name), VarSymbol):
            return self.assignment[Cell(expr.name)]
        if isinstance(expr, Access) and isinstance(symbols[expr.name], VarSymbol):
            key = tuple(evaluate(i, symbols, env) for i in expr.indices)
            return self.assignment[Cell(expr.name, key)]
        if isinstance(expr, Compare):
            return compare_values(expr.op, self.value(expr.left, env), self.value(expr.right, env))
        if isinstance(expr, Not):
            return not self.value(expr.expr, env)
        if isinstance(expr, And):
            return self.value(expr.left, env) and self.value(expr.right, env)
        if isinstance(expr, Or):
            return self.value(expr.left, env) or self.value(expr.right, env)
        if isinstance(expr, Implies):
            return not self.value(expr.left, env) or self.value(expr.right, env)
        if isinstance(expr, Call) and expr.name != "abs":
            values = []
            for arg in expr.args:
                if isinstance(arg, Access) and any(isinstance(i, Star) for i in arg.indices):
                    symbol = symbols[arg.name]
                    choices = [d.values if isinstance(i, Star) else (evaluate(i, symbols, env),)
                               for i, d in zip(arg.indices, symbol.dims)]
                    for key in product(*choices):
                        if isinstance(symbol, VarSymbol):
                            values.append(self.assignment[Cell(arg.name, key)])
                        else:
                            values.append(symbol.values[key])
                else:
                    values.append(self.value(arg, env))
            return holds_globally(expr.name, values)
        return evaluate(expr, symbols, env)

    def statement(self, statement, env: dict) -> bool:
        if isinstance(statement, Constraint):
            return self.value(statement.expr, env)
        return self.loop(statement, 0, env)

    def loop(self, loop, number: int, env: dict) -> bool:
        if number == len(loop.iterators):
            return all(self.statement(s, env) for s in loop.body)
        iterator = loop.iterators[number]
        domain = iterator.domain
        if hasattr(domain, "low"):
            values = range(evaluate(domain.low, self.model.symbols, env),
                           evaluate(domain.high, self.model.symbols, env) + 1)
        else:
            values = self.model.symbols[domain.name].values.values
        return all(self.loop(loop, number + 1, {**env, iterator.name: v}) for v in values)


def formula_value(formula, assignment: dict):
    if isinstance(formula, Cell):
        return assignment[formula]
    if isinstance(formula, (bool, int, EnumValue)):
        return formula
    if isinstance(formula, Compare):
        return compare_values(formula.op, formula_value(formula.left, assignment),
                              formula_value(formula.right, assignment))
    if isinstance(formula, Not):
        return not formula_value(formula.expr, assignment)
    if isinstance(formula, And):
        return formula_value(formula.left, assignment) and formula_value(formula.right, assignment)
    if isinstance(formula, Or):
        return formula_value(formula.left, assignment) or formula_value(formula.right, assignment)
    if isinstance(formula, Implies):
        return (not formula_value(formula.left, assignment)) or formula_value(formula.right, assignment)
    return holds_globally(formula.name, [formula_value(a, assignment) for a in formula.args])


class TestsEquivalence(unittest.TestCase):
    MODELS = [
        "var x : 1..3; var y : 1..3;\n"
        "constraint not x = 2 or 3 < y;\n"
        "constraint x > y -> not (x <= y);\n"
        "constraint not (y >= x) -> y != 1;",

        "array b[3] : bool;\n"
        "constraint atMostOne(b[*]);\n"
        "constraint exactlyOne(b[1], b[2], 1 < 2 and b[3]) or b[1];\n"
        "constraint atLeastOne(b[2], 2 > 3, b[3]);",

        "enum C = { R, G, B }; array c[2] : C;\n"
        "constraint c[1] < c[2] or c[1] = B;\n"
        "constraint allDifferent(c[*], G);",

        "const N = 3; array g[N] : 1..2;\n"
        "forall i in 1..N { constraint i < N -> g[i + 1] >= g[i]; }\n"
        "forall i in 1..N, j in i..N { constraint i != j -> not (g[i] = 1 and g[j] = 1); }",

        "var p : bool; var q : bool;\n"
        "constraint (p = q) != (not p);\n"
        "constraint q != (1 > 2) -> p;",
    ]
    # Une seule comparaison par modèle, dans chaque position : une erreur de
    # normalisation sur un opérateur ne peut pas être masquée.
    for op in ("=", "!=", "<", "<=", ">", ">="):
        MODELS += [
            f"var x : 1..3; var y : 2..4; constraint x {op} y;",
            f"var x : 1..3; var y : 2..4; constraint not x {op} y;",
            f"var x : 1..3; constraint x {op} 2;",
            f"var x : 1..3; constraint 2 {op} x;",
            f"var x : 1..3; constraint not 2 {op} x;",
        ]
    del op

    def test_memes_solutions_que_le_modele_source(self):
        for text in self.MODELS:
            with self.subTest(model=text):
                model = analyse(parse(text))
                constraints = expand(model).constraints
                all_cells = [(Cell(v.name, key), v.domain.values)
                             for v in model.variables for key in cells(v)]
                solutions = 0
                for values in product(*(domain for _, domain in all_cells)):
                    assignment = {cell: value for (cell, _), value in zip(all_cells, values)}
                    source = all(SourceInterpreter(model, assignment).statement(s, {})
                                 for s in model.statements)
                    result = all(formula_value(c, assignment) for c in constraints)
                    self.assertEqual(source, result, assignment)
                    solutions += source
                self.assertGreater(solutions, 0)


class TestsModelesDuSujet(unittest.TestCase):
    def test_les_quatre_modeles_sont_deroules(self):
        expected = {
            "pigeonhole.csp": 1,     # un allDifferent sur les 4 pigeons
            "coloring.csp": 17,      # 15 arêtes et 2 couleurs fixées
            "sudoku.csp": 57,        # 27 allDifferent et 30 cases données
            "queens.csp": 281,       # un allDifferent et 280 paires en diagonale
        }
        for name, count in expected.items():
            with self.subTest(model=name):
                expansion = expand(analyse(parse((EXEMPLES / name).read_text(encoding="utf-8"))))
                self.assertEqual(len(expansion.constraints), count)
                self.assertEqual(expansion.warnings, [])

    def test_les_dames_ne_gardent_que_les_diagonales(self):
        constraints = expanded((EXEMPLES / "queens.csp").read_text(encoding="utf-8"))
        self.assertIn("not (queen[1] = 1 and queen[2] = 2)", constraints)
        self.assertNotIn("not (queen[1] = 1 and queen[2] = 3)", constraints)
        # 8 reines : chaque paire de lignes i < j a 2 * (8 - (j - i)) couples interdits
        pairs = sum(2 * (8 - (j - i)) for i in range(1, 9) for j in range(i + 1, 9))
        self.assertEqual(pairs, 280)

    def test_le_sudoku_fixe_les_cases_donnees(self):
        constraints = expanded((EXEMPLES / "sudoku.csp").read_text(encoding="utf-8"))
        self.assertIn("grid[1][1] = 5", constraints)
        self.assertIn("grid[9][9] = 9", constraints)


if __name__ == "__main__":
    unittest.main()
