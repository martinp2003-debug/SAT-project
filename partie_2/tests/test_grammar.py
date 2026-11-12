"""Question 2 : tests de la grammaire du langage complet et de l'AST.

Les tests suivent l'ordre de la question :

1. chaque construction du langage donne le nœud attendu ;
2. les priorités et associativités des nouveaux opérateurs ;
3. les erreurs de syntaxe, avec leur position ;
4. les positions conservées dans l'arbre et les messages d'erreur ;
5. les quatre modèles du sujet sont acceptés, et l'impression de leur arbre
   en source puis sa relecture redonnent le même arbre.

Ces tests ne vérifient que la forme du texte : un nom non déclaré ou une
tranche hors d'une contrainte globale sont acceptés ici et seront rejetés
par l'analyse sémantique (question 3).
"""

from pathlib import Path
import unittest

from lark.exceptions import UnexpectedInput

from syntax import (
    Access,
    And,
    ArrayDecl,
    ArrayLiteral,
    BinOp,
    Call,
    Compare,
    Constraint,
    ConstDecl,
    EnumDecl,
    EnumDomain,
    Forall,
    Implies,
    IntLit,
    Iterator,
    Neg,
    Not,
    Or,
    RangeDomain,
    Star,
    Var,
    VarDecl,
    parse,
    position,
    pretty,
    syntax_error_message,
    to_source,
)


EXEMPLES = Path(__file__).resolve().parent.parent / "exemples"

a, b, c, x = Var("a"), Var("b"), Var("c"), Var("x")


def parse_expr(text: str) -> object:
    """L'arbre d'une expression, par exemple ``Compare("=", x, IntLit(2))``."""
    return parse(f"constraint {text};").statements[0].expr


class TestsConstructions(unittest.TestCase):
    """Chaque construction du langage produit son nœud d'AST."""

    def test_declarations(self):
        cases = [
            ("const N = 9;", ConstDecl("N", [], IntLit(9))),
            (
                "const r[2][3] = [[1, 1, 2], [3, 3, 2]];",
                ConstDecl(
                    "r",
                    [IntLit(2), IntLit(3)],
                    ArrayLiteral([
                        ArrayLiteral([IntLit(1), IntLit(1), IntLit(2)]),
                        ArrayLiteral([IntLit(3), IntLit(3), IntLit(2)]),
                    ]),
                ),
            ),
            (
                "enum Color = { Red, Green, Blue };",
                EnumDecl("Color", ["Red", "Green", "Blue"]),
            ),
            ("var b : bool;", VarDecl("b", EnumDomain("bool"))),
            ("var x : 1..N;", VarDecl("x", RangeDomain(IntLit(1), Var("N")))),
            ("var c : Color;", VarDecl("c", EnumDomain("Color"))),
            (
                "array grid[N][N] : 1..N;",
                ArrayDecl("grid", [Var("N"), Var("N")], RangeDomain(IntLit(1), Var("N"))),
            ),
            (
                "array used[Color] : bool;",
                ArrayDecl("used", [Var("Color")], EnumDomain("bool")),
            ),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(parse(text).statements, [expected])

    def test_boucles_imbriquees_et_domaines_calcules(self):
        program = parse(
            "forall i in 1..N, j in i..N { constraint a;"
            " forall c2 in Color { constraint b; } }"
        )
        expected = Forall(
            [
                Iterator("i", RangeDomain(IntLit(1), Var("N"))),
                Iterator("j", RangeDomain(Var("i"), Var("N"))),
            ],
            [
                Constraint(a),
                Forall([Iterator("c2", EnumDomain("Color"))], [Constraint(b)]),
            ],
        )
        self.assertEqual(program.statements, [expected])
        loop = parse("forall k in (i - 1)..(i + 1) { constraint a; }").statements[0]
        self.assertEqual(
            loop.iterators[0].domain,
            RangeDomain(BinOp("-", Var("i"), IntLit(1)), BinOp("+", Var("i"), IntLit(1))),
        )

    def test_acces_tranches_et_appels(self):
        self.assertEqual(
            parse_expr("grid[i + 1][j] != grid[i][j]"),
            Compare(
                "!=",
                Access("grid", [BinOp("+", Var("i"), IntLit(1)), Var("j")]),
                Access("grid", [Var("i"), Var("j")]),
            ),
        )
        self.assertEqual(
            parse_expr("allDifferent(grid[1][*], grid[*][*], x)"),
            Call("allDifferent", [
                Access("grid", [IntLit(1), Star()]),
                Access("grid", [Star(), Star()]),
                x,
            ]),
        )
        self.assertEqual(
            parse_expr("color[edge[e][1]] = Red"),
            Compare("=", Access("color", [Access("edge", [Var("e"), IntLit(1)])]), Var("Red")),
        )
        self.assertEqual(parse_expr("f()"), Call("f", []))

    def test_les_six_comparaisons(self):
        for op in ("=", "!=", "<", "<=", ">", ">="):
            with self.subTest(op=op):
                self.assertEqual(parse_expr(f"a {op} b"), Compare(op, a, b))

    def test_l_etoile_est_une_multiplication_hors_des_crochets(self):
        self.assertEqual(
            parse_expr("grid[3*bi + 1][*] = 2"),
            Compare(
                "=",
                Access("grid", [BinOp("+", BinOp("*", IntLit(3), Var("bi")), IntLit(1)), Star()]),
                IntLit(2),
            ),
        )


class TestsPriorites(unittest.TestCase):
    """Priorités et associativités, encodées par les niveaux de la grammaire."""

    def test_priorites(self):
        cases = [
            ("not x = 2", Not(Compare("=", x, IntLit(2)))),
            ("x = 2 and b", And(Compare("=", x, IntLit(2)), b)),
            ("a < b or c", Or(Compare("<", a, b), c)),
            ("a + b * c", BinOp("+", a, BinOp("*", b, c))),
            ("a * b + c", BinOp("+", BinOp("*", a, b), c)),
            ("-a * b", BinOp("*", Neg(a), b)),
            ("a - -b", BinOp("-", a, Neg(b))),
            ("(a + b) * c", BinOp("*", BinOp("+", a, b), c)),
            ("a + 1 = b * 2", Compare("=", BinOp("+", a, IntLit(1)), BinOp("*", b, IntLit(2)))),
            (
                "i < N -> x != 3",
                Implies(Compare("<", Var("i"), Var("N")), Compare("!=", x, IntLit(3))),
            ),
            ("abs(a - b) = c", Compare("=", Call("abs", [BinOp("-", a, b)]), c)),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(parse_expr(text), expected)

    def test_associativite_a_gauche_de_l_arithmetique(self):
        self.assertEqual(parse_expr("a - b - c"), BinOp("-", BinOp("-", a, b), c))
        self.assertEqual(parse_expr("a * b * c"), BinOp("*", BinOp("*", a, b), c))


class TestsErreursDeSyntaxe(unittest.TestCase):
    """Les textes mal formés sont rejetés, avec la position de l'erreur."""

    def test_erreurs_et_positions(self):
        cases = [
            ("constraint a = b = c;", (1, 18)),        # pas de comparaisons en chaîne
            ("constraint a < b > c;", (1, 18)),
            ("constraint not x = 2 = 3;", (1, 22)),
            ("var const : bool;", (1, 5)),             # mot-clé réservé
            ("const N = 9", (1, 11)),                  # ";" manquant
            ("var x : 1..N", (1, 12)),
            ("var x : int..;", (1, 14)),               # borne manquante
            ("array a[] : bool;", (1, 9)),             # taille manquante
            ("enum C = { };", (1, 12)),                # énumération vide
            ("constraint grid[i][*;", (1, 21)),
            ("forall i in 1..N { var x : bool; }", (1, 20)),  # pas de déclaration dans une boucle
        ]
        for text, position in cases:
            with self.subTest(text=text):
                with self.assertRaises(UnexpectedInput) as error:
                    parse(text)
                self.assertEqual((error.exception.line, error.exception.column), position)

    def test_les_onze_mots_cles_sont_reserves(self):
        keywords = ["const", "enum", "var", "array", "bool", "constraint",
                    "forall", "in", "not", "and", "or"]
        for keyword in keywords:
            with self.subTest(keyword=keyword):
                with self.assertRaises(UnexpectedInput):
                    parse(f"var {keyword} : bool;")

    def test_les_fonctions_ne_sont_pas_des_mots_cles(self):
        for name in ("abs", "allDifferent", "atMostOne"):
            with self.subTest(name=name):
                self.assertEqual(
                    parse(f"var {name} : bool;").statements,
                    [VarDecl(name, EnumDomain("bool"))],
                )


class TestsPositionsEtMessages(unittest.TestCase):
    """Chaque nœud garde sa position ; les erreurs de syntaxe sont expliquées."""

    def test_chaque_noeud_connait_sa_ligne_et_sa_colonne(self):
        program = parse("var x : bool;\n  constraint not w and x;")
        declaration, constraint = program.statements
        self.assertEqual((declaration.line, declaration.column), (1, 1))
        self.assertEqual((constraint.line, constraint.column), (2, 3))
        self.assertEqual((constraint.expr.line, constraint.expr.column), (2, 14))
        w = constraint.expr.left.expr
        self.assertEqual((w, w.line, w.column), (Var("w"), 2, 18))

    def test_la_position_ne_compte_pas_dans_l_egalite(self):
        self.assertEqual(parse_expr("x"), Var("x"))
        self.assertEqual(position(Var("x")), "")
        self.assertEqual(position(parse_expr("x")), "ligne 1, colonne 12 : ")

    def test_messages_d_erreur_de_syntaxe(self):
        cases = [
            (
                "var x : bool;\nconstraint x and;",
                "ligne 2, colonne 17 : « ; » inattendu, attendu : "
                "un entier, un nom, « ( », « - » ou « not »",
            ),
            ("var and : bool;", "ligne 1, colonne 5 : « and » inattendu, attendu : un nom"),
            ("constraint x @ y;", "ligne 1, colonne 14 : caractère « @ » inattendu"),
            ("const N = 9", "ligne 1, colonne 11 : fin du fichier inattendue"),
        ]
        for text, message in cases:
            with self.subTest(text=text):
                with self.assertRaises(UnexpectedInput) as error:
                    parse(text)
                self.assertTrue(
                    syntax_error_message(error.exception).startswith(message),
                    syntax_error_message(error.exception),
                )


class TestsModelesDuSujet(unittest.TestCase):
    """Les quatre modèles d'exemples/ sont acceptés et relus à l'identique."""

    def test_les_quatre_modeles_sont_acceptes(self):
        paths = sorted(EXEMPLES.glob("*.csp"))
        self.assertEqual(
            [path.name for path in paths],
            ["coloring.csp", "pigeonhole.csp", "queens.csp", "sudoku.csp"],
        )
        for path in paths:
            with self.subTest(model=path.name):
                program = parse(path.read_text(encoding="utf-8"))
                self.assertTrue(program.statements)

    def test_aller_retour_source_arbre(self):
        for path in sorted(EXEMPLES.glob("*.csp")):
            with self.subTest(model=path.name):
                program = parse(path.read_text(encoding="utf-8"))
                self.assertEqual(parse(to_source(program)), program)

    def test_affichage_de_l_arbre(self):
        program = parse((EXEMPLES / "pigeonhole.csp").read_text(encoding="utf-8"))
        self.assertEqual(
            pretty(program),
            "Program\n"
            "  Const P = 4\n"
            "  Const H = 3\n"
            "  Array hole[P] : 1..H\n"
            "  Constraint allDifferent(hole[*])",
        )


if __name__ == "__main__":
    unittest.main()
