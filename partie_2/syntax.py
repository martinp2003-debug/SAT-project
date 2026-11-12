r"""
Syntax of the constraint language: grammar (Lark, LALR), AST,
pretty-printer and source printer.

    text --(Lark parser)--> parse tree --(ASTBuilder)--> AST

The parse tree is Lark's generic tree (Tree / Token objects, one node per
grammar rule). The AST is made of our own dataclasses (below), one class per
construct of the language, which later passes walk with isinstance.

Example. The text

    var x : bool;
    var y : bool;
    constraint not x and y -> x or y;

gives the AST, as printed by pretty() (`python csp.py model.csp --ast`)

    Program
      Var x : bool
      Var y : bool
      Constraint (((!x) /\ y) -> (x \/ y))
"""

from dataclasses import dataclass, field

from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedInput, UnexpectedToken


# Lark notation used in GRAMMAR:
# - "rule: ..." defines a rule; each rule gives a node of the parse tree.
# - "?rule: ...": when the rule has a single child, the child replaces the
#   node. An atom that is a reference is just the reference, no "atom" node.
# - "... -> name" names the node of that alternative, and thus the
#   ASTBuilder method called on it.
# - "..." strings (keywords, punctuation) are matched, then dropped from
#   the tree.
# - NAME is Lark's common.CNAME (identifiers). Whitespace (WS) and //
#   comments (CPP_COMMENT) are skipped with %ignore.
#
# The lexer is "basic" (see `parser` below): it cuts the whole text into
# tokens before parsing, and a keyword ("var", "and", "bool", ...) always
# gives a keyword token, never a NAME. Keywords are thus reserved:
# `var and : bool;` is a syntax error. (Lark's default lexer would decide
# from the context of the parser, and accept it.)

GRAMMAR = r"""
?start: program

program: statement*

?statement: const_decl
          | enum_decl
          | var_decl
          | array_decl
          | constraint_decl
          | forall_stmt

// -------------------- STATEMENTS --------------------

// const N = 9;    const region[2][3] = [[1, 1, 2], [3, 3, 2]];
const_decl: "const" NAME "=" arith ";"
          | "const" NAME dims "=" array_literal ";"  -> const_array_decl

array_literal: "[" element ("," element)* "]"
?element: arith
        | array_literal

// enum Color = { Red, Green, Blue };
enum_decl: "enum" NAME "=" "{" NAME ("," NAME)* "}" ";"

// var x : bool;    var x : 1..N;    var c : Color;
var_decl: "var" NAME ":" domain ";"

// array grid[N][N] : 1..N;    array used[Color] : bool;
array_decl: "array" NAME dims ":" domain ";"

// A size is a known integer or an enum type name: both are arith here,
// the semantic analysis (question 3) tells them apart.
dims: ("[" arith "]")+

// After a NAME, the parser reduces it to a domain if the next token ends
// the domain (";", "," or "{"), and to an expression if it is ".." or an
// operator: the lookahead is enough, LALR(1) has no conflict.
?domain: "bool"                         -> bool_domain
       | arith ".." arith               -> range_domain
       | NAME                           -> named_domain

// constraint x or y;
constraint_decl: "constraint" expr ";"

// forall i in 1..N, j in i..N { ... }   (loops only contain constraints)
forall_stmt: "forall" iterator ("," iterator)* "{" body_statement* "}"
iterator: NAME "in" domain
?body_statement: constraint_decl
               | forall_stmt

// -------------------- EXPRESSIONS --------------------
//
// Precedence is encoded by layering the rules, from the loosest to the
// tightest:
//     ->  <  or  <  and  <  not  <  comparisons  <  + -  <  *
//         <  unary -  <  atom
// Each layer either is the next one (the "?" rule is then inlined, no
// node), or combines the next ones with its operator.
//     a or b and c      parses as  a or (b and c)
//     not a and b       parses as  (not a) and b
//     a -> b -> c       parses as  a -> (b -> c)     (right recursive)
//     a or b or c       parses as  (a or b) or c     (left recursive)
//     not x = 2         parses as  not (x = 2)
//     a - b - c         parses as  (a - b) - c       (left recursive)
//     a + b * c         parses as  a + (b * c)
// A comparison has two arith operands, never a comparison: a = b = c is
// a syntax error.

?expr: implication

?implication: or_expr
            | or_expr "->" implication  -> implies

?or_expr: and_expr
        | or_expr "or" and_expr         -> or_op

?and_expr: not_expr
         | and_expr "and" not_expr      -> and_op

?not_expr: "not" not_expr               -> not_op
         | comparison

?comparison: arith
           | arith "=" arith            -> eq
           | arith "!=" arith           -> ne
           | arith "<" arith            -> lt
           | arith "<=" arith           -> le
           | arith ">" arith            -> gt
           | arith ">=" arith           -> ge

?arith: term
      | arith "+" term                  -> add
      | arith "-" term                  -> sub

?term: factor
     | term "*" factor                  -> mul

?factor: "-" factor                     -> neg
       | atom

?atom: INT                              -> int_lit
     | reference
     | NAME "(" ")"                     -> call
     | NAME "(" argument ("," argument)* ")"  -> call
     | "(" expr ")"

// grid[i][j]; "*" as an index is the wildcard of a slice, grid[i][*].
// After "[", a "*" cannot start an expression, so it is never confused
// with the multiplication. Slices are accepted wherever an access is;
// the semantic analysis (question 3) only allows them as arguments of a
// global constraint.
?reference: NAME                        -> var_ref
          | reference "[" index "]"     -> access
?index: arith
      | "*"                             -> star

?argument: expr

%import common.CNAME -> NAME
%import common.INT
%import common.WS
%import common.CPP_COMMENT
%ignore WS
%ignore CPP_COMMENT
"""


# ------------------------------------------------------------
# AST
# ------------------------------------------------------------
# One dataclass per construct (avoids the need for __init__())
#
# Every node also keeps the position (line, column) where it starts in the
# text, so that later passes can say where an error is. The position is a
# keyword-only field left out of == and of the printed form: two trees that
# differ only by their positions are equal, and nodes can still be built by
# hand without one, e.g. Var("x").

@dataclass
class Node:
    line: int | None = field(default=None, kw_only=True, compare=False, repr=False)
    column: int | None = field(default=None, kw_only=True, compare=False, repr=False)


# Statements

@dataclass
class Program(Node):
    statements: list

class Domain(Node):
    pass

# "bool" is the boolean domain; an enum type name (var c : Color;) is also
# an EnumDomain. Whether the name really is an enum type is checked later.
@dataclass
class EnumDomain(Domain):
    name: str

# a..b, bounds are expressions that must be known (checked later)
@dataclass
class RangeDomain(Domain):
    low: object
    high: object

@dataclass
class ConstDecl(Node):
    """const N = 9; dims is [] for an integer, the sizes for an array."""
    name: str
    dims: list
    value: object

@dataclass
class ArrayLiteral(Node):
    """[e1, ..., en]: the elements are expressions or ArrayLiterals."""
    elements: list

@dataclass
class EnumDecl(Node):
    name: str
    values: list

@dataclass
class VarDecl(Node):
    name: str
    domain: Domain

@dataclass
class ArrayDecl(Node):
    """array grid[N][N] : 1..N; a size is an expression or an enum name."""
    name: str
    dims: list
    domain: Domain

@dataclass
class Constraint(Node):
    expr: object

@dataclass
class Iterator(Node):
    """i in 1..N (RangeDomain) or c in Color (EnumDomain)."""
    name: str
    domain: Domain

@dataclass
class Forall(Node):
    iterators: list
    body: list


# Expressions

@dataclass
class Var(Node):
    """A name used as a value: x in `constraint x or y;`.

    The name may also be a constant, an enum value or a loop index: the
    parser cannot tell them apart, the symbol table will.
    """
    name: str

@dataclass
class IntLit(Node):
    value: int

@dataclass
class Access(Node):
    """grid[i][j] is Access("grid", [i, j]); Star() is the wildcard *."""
    name: str
    indices: list

@dataclass
class Star(Node):
    pass

@dataclass
class Call(Node):
    """allDifferent(...), abs(...): functions are not keywords."""
    name: str
    args: list

@dataclass
class Compare(Node):
    op: str     # one of = != < <= > >=
    left: object
    right: object

@dataclass
class BinOp(Node):
    op: str     # one of + - *
    left: object
    right: object

@dataclass
class Neg(Node):
    expr: object

@dataclass
class And(Node):
    left: object
    right: object

@dataclass
class Or(Node):
    left: object
    right: object

@dataclass
class Not(Node):
    expr: object

@dataclass
class Implies(Node):
    left: object
    right: object


def _keep_position(method, _data, children, meta):
    """Calls a builder method, then copies the Lark position into the node."""
    node = method(children)
    if isinstance(node, Node) and not meta.empty:
        node.line, node.column = meta.line, meta.column
    return node


@v_args(wrapper=_keep_position)
class ASTBuilder(Transformer):
    """
    Turns the Lark parse tree into the AST, bottom-up: Lark calls the method
    named after each rule (or alias) of the grammar, with its children
    (items), already transformed, without the dropped "..." strings.
    For "var x : bool;" (rule var_decl), items is ["x", EnumDomain("bool")]:
    NAME() below has already turned the token into a str, and bool_domain()
    the domain into an EnumDomain.

    The value returned replaces the node in its parent's items.
    """

    def program(self, items):
        return Program(items)

    def const_decl(self, items):
        return ConstDecl(items[0], [], items[1])

    def const_array_decl(self, items):
        return ConstDecl(items[0], items[1], items[2])

    def array_literal(self, items):
        return ArrayLiteral(items)

    def enum_decl(self, items):
        return EnumDecl(items[0], items[1:])

    def var_decl(self, items):
        return VarDecl(items[0], items[1])

    def array_decl(self, items):
        return ArrayDecl(items[0], items[1], items[2])

    def dims(self, items):
        return items

    def bool_domain(self, items):
        return EnumDomain("bool")

    def range_domain(self, items):
        return RangeDomain(items[0], items[1])

    def named_domain(self, items):
        return EnumDomain(items[0])

    def constraint_decl(self, items):
        return Constraint(items[0])

    def forall_stmt(self, items):
        iterators = [item for item in items if isinstance(item, Iterator)]
        body = items[len(iterators):]
        return Forall(iterators, body)

    def iterator(self, items):
        return Iterator(items[0], items[1])

    # Expressions

    def NAME(self, items):
        return str(items)

    def INT(self, items):
        return int(items)

    def int_lit(self, items):
        return IntLit(items[0])

    def var_ref(self, items):
        return Var(items[0])

    def access(self, items):
        target, index = items
        if isinstance(target, Access):     # grid[i][j]: add j to grid[i]
            return Access(target.name, target.indices + [index])
        return Access(target.name, [index])

    def star(self, items):
        return Star()

    def call(self, items):
        return Call(items[0], items[1:])

    def eq(self, items):
        return Compare("=", items[0], items[1])

    def ne(self, items):
        return Compare("!=", items[0], items[1])

    def lt(self, items):
        return Compare("<", items[0], items[1])

    def le(self, items):
        return Compare("<=", items[0], items[1])

    def gt(self, items):
        return Compare(">", items[0], items[1])

    def ge(self, items):
        return Compare(">=", items[0], items[1])

    def add(self, items):
        return BinOp("+", items[0], items[1])

    def sub(self, items):
        return BinOp("-", items[0], items[1])

    def mul(self, items):
        return BinOp("*", items[0], items[1])

    def neg(self, items):
        return Neg(items[0])

    def and_op(self, items):
        return And(items[0], items[1])

    def or_op(self, items):
        return Or(items[0], items[1])

    def not_op(self, items):
        return Not(items[0])

    def implies(self, items):
        return Implies(items[0], items[1])


# propagate_positions: Lark computes the position of every node (its meta),
# which _keep_position copies into the AST.
parser = Lark(GRAMMAR, parser="lalr", lexer="basic", propagate_positions=True)


def parse(text: str) -> Program:
    """Parse a whole model. A syntax error raises Lark's UnexpectedInput."""
    tree = parser.parse(text)
    return ASTBuilder().transform(tree)


def position(node) -> str:
    """ "ligne 3, colonne 12 : " for a node read from a text, "" otherwise."""
    if getattr(node, "line", None) is None:
        return ""
    return f"ligne {node.line}, colonne {node.column} : "


# Names shown to the user for the terminals that are not plain strings.
_TERMINAL_NAMES = {"NAME": "un nom", "INT": "un entier", "$END": "la fin du fichier"}


def _describe_terminal(name: str) -> str:
    if name in _TERMINAL_NAMES:
        return _TERMINAL_NAMES[name]
    pattern = parser.get_terminal(name).pattern
    return f"« {pattern.value} »"


def syntax_error_message(error: UnexpectedInput) -> str:
    """Explains a Lark syntax error in a short sentence, with its position.

    Example: "ligne 2, colonne 17 : « ; » inattendu, attendu : un nom,
    un entier, « ( », « - » ou « not »".
    """
    where = f"ligne {error.line}, colonne {error.column} : "
    if isinstance(error, UnexpectedCharacters):
        return where + f"caractère « {error.char} » inattendu"
    if isinstance(error, UnexpectedToken):
        if error.token.type == "$END":
            found = "fin du fichier inattendue"
        else:
            found = f"« {error.token} » inattendu"
        expected = sorted(_describe_terminal(name) for name in error.expected)
        if not expected:
            return where + found
        if len(expected) == 1:
            return where + f"{found}, attendu : {expected[0]}"
        return where + f"{found}, attendu : {', '.join(expected[:-1])} ou {expected[-1]}"
    return where + "erreur de syntaxe"


# ------------------------------------------------------------
# Pretty-printer
# ------------------------------------------------------------
# Shows the structure of the tree: one statement per line, and every
# binary or unary expression in parentheses, so that the precedences
# chosen by the parser can be read off.

def pretty(node) -> str:
    if isinstance(node, Program):
        lines = ["Program"]
        for statement in node.statements:
            lines.extend("  " + line for line in pretty(statement).split("\n"))
        return "\n".join(lines)
    if isinstance(node, ConstDecl):
        return f"Const {node.name}{_dims(node.dims, pretty)} = {pretty(node.value)}"
    if isinstance(node, EnumDecl):
        return f"Enum {node.name} = {{{', '.join(node.values)}}}"
    if isinstance(node, VarDecl):
        return f"Var {node.name} : {pretty(node.domain)}"
    if isinstance(node, ArrayDecl):
        return f"Array {node.name}{_dims(node.dims, pretty)} : {pretty(node.domain)}"
    if isinstance(node, Constraint):
        return "Constraint " + pretty(node.expr)
    if isinstance(node, Forall):
        lines = ["Forall " + ", ".join(pretty(i) for i in node.iterators)]
        for statement in node.body:
            lines.extend("  " + line for line in pretty(statement).split("\n"))
        return "\n".join(lines)
    if isinstance(node, Iterator):
        return f"{node.name} in {pretty(node.domain)}"
    if isinstance(node, EnumDomain):
        return node.name
    if isinstance(node, RangeDomain):
        return f"{pretty(node.low)}..{pretty(node.high)}"
    if isinstance(node, ArrayLiteral):
        return "[" + ", ".join(pretty(e) for e in node.elements) + "]"
    if isinstance(node, Var):
        return node.name
    if isinstance(node, IntLit):
        return str(node.value)
    if isinstance(node, Star):
        return "*"
    if isinstance(node, Access):
        return node.name + _dims(node.indices, pretty)
    if isinstance(node, Call):
        return f"{node.name}({', '.join(pretty(a) for a in node.args)})"
    if isinstance(node, Not):
        return f"(!{pretty(node.expr)})"
    if isinstance(node, And):
        return f"({pretty(node.left)} /\\ {pretty(node.right)})"
    if isinstance(node, Or):
        return f"({pretty(node.left)} \\/ {pretty(node.right)})"
    if isinstance(node, Implies):
        return f"({pretty(node.left)} -> {pretty(node.right)})"
    if isinstance(node, (Compare, BinOp)):
        return f"({pretty(node.left)} {node.op} {pretty(node.right)})"
    if isinstance(node, Neg):
        return f"(-{pretty(node.expr)})"
    raise TypeError(f"pretty: unexpected node {node!r}")


def _dims(indices: list, show) -> str:
    return "".join(f"[{show(index)}]" for index in indices)


# ------------------------------------------------------------
# Source printer
# ------------------------------------------------------------
# Prints the AST back in the language itself, with every compound
# expression in parentheses. Parsing this text gives the same AST again:
#     parse(to_source(program)) == program
# which checks that the parser and the printer agree (see the tests).

def to_source(node) -> str:
    if isinstance(node, Program):
        return "\n".join(to_source(s) for s in node.statements) + "\n"
    if isinstance(node, ConstDecl):
        return f"const {node.name}{_dims(node.dims, to_source)} = {to_source(node.value)};"
    if isinstance(node, EnumDecl):
        return f"enum {node.name} = {{ {', '.join(node.values)} }};"
    if isinstance(node, VarDecl):
        return f"var {node.name} : {to_source(node.domain)};"
    if isinstance(node, ArrayDecl):
        return (f"array {node.name}{_dims(node.dims, to_source)}"
                f" : {to_source(node.domain)};")
    if isinstance(node, Constraint):
        return f"constraint {to_source(node.expr)};"
    if isinstance(node, Forall):
        iterators = ", ".join(to_source(i) for i in node.iterators)
        body = " ".join(to_source(s) for s in node.body)
        return f"forall {iterators} {{ {body} }}"
    if isinstance(node, Iterator):
        return f"{node.name} in {to_source(node.domain)}"
    if isinstance(node, EnumDomain):
        return node.name
    if isinstance(node, RangeDomain):
        return f"{to_source(node.low)}..{to_source(node.high)}"
    if isinstance(node, ArrayLiteral):
        return "[" + ", ".join(to_source(e) for e in node.elements) + "]"
    if isinstance(node, Var):
        return node.name
    if isinstance(node, IntLit):
        return str(node.value)
    if isinstance(node, Star):
        return "*"
    if isinstance(node, Access):
        return node.name + _dims(node.indices, to_source)
    if isinstance(node, Call):
        return f"{node.name}({', '.join(to_source(a) for a in node.args)})"
    if isinstance(node, Not):
        return f"(not {to_source(node.expr)})"
    if isinstance(node, And):
        return f"({to_source(node.left)} and {to_source(node.right)})"
    if isinstance(node, Or):
        return f"({to_source(node.left)} or {to_source(node.right)})"
    if isinstance(node, Implies):
        return f"({to_source(node.left)} -> {to_source(node.right)})"
    if isinstance(node, (Compare, BinOp)):
        return f"({to_source(node.left)} {node.op} {to_source(node.right)})"
    if isinstance(node, Neg):
        return f"(- {to_source(node.expr)})"
    raise TypeError(f"to_source: unexpected node {node!r}")
