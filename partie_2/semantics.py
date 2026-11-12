"""Question 3, analysis: symbol table, types and known values.

    AST (syntax.py) --analyse()--> Model --expand() (expansion.py)--> constraints

analyse() reads the declarations in order and builds the symbol table:
constants are evaluated, domains and array sizes computed. It then checks the
types of every constraint, inside the scope of its loops, without unrolling
them. A model accepted here only needs values to be computed: the only errors
left to expansion are those that depend on a value (an index out of range).

Types are int, bool and one type per enum. An expression is *known* when it
only depends on literals, constants, enum values and loop indices: sizes,
bounds, indices and the operands of arithmetic must be known.
"""

from dataclasses import dataclass
from itertools import product

from diagnostics import CompilationError
from syntax import (
    Access,
    And,
    ArrayDecl,
    ArrayLiteral,
    BinOp,
    Call,
    Compare,
    ConstDecl,
    Constraint,
    EnumDecl,
    EnumDomain,
    Implies,
    IntLit,
    Neg,
    Not,
    Or,
    Program,
    Star,
    Var,
    VarDecl,
    position,
)


# ------------------------------------------------------------
# Types, values and symbols
# ------------------------------------------------------------

@dataclass(frozen=True)
class Type:
    kind: str               # "int", "bool" or "enum"
    enum: str | None = None

    def __str__(self) -> str:
        return {"int": "entier", "bool": "booléen"}.get(self.kind, self.enum)


INT = Type("int")
BOOL = Type("bool")


@dataclass(frozen=True)
class EnumValue:
    """A value of an enum type, ordered by its index of declaration."""
    type: str
    index: int
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Values:
    """A finite ordered set of values of one type: a domain or an index set.

    1..3 is Values(INT, (1, 2, 3)), bool is Values(BOOL, (False, True)).
    """
    type: Type
    values: tuple

    def describe(self) -> str:
        if self.type == INT:
            return f"{self.values[0]}..{self.values[-1]}"
        return self.type.enum if self.type.kind == "enum" else "bool"


@dataclass
class ConstSymbol:
    """A constant; for an array, values maps each index tuple to its value."""
    name: str
    type: Type
    dims: list          # list[Values], [] for a scalar
    values: dict        # {(): value} for a scalar


@dataclass
class EnumSymbol:
    name: str
    values: Values


@dataclass
class EnumValueSymbol:
    value: EnumValue


@dataclass
class VarSymbol:
    """A variable (dims == []) or an array of variables."""
    name: str
    dims: list          # list[Values]
    domain: Values


@dataclass
class Model:
    """The checked model: symbols, variables and loop-level statements."""
    symbols: dict
    variables: list     # VarSymbol, in declaration order
    statements: list    # Constraint and Forall nodes, in order


GLOBALS = {"atLeastOne", "atMostOne", "exactlyOne", "allDifferent"}


def error(node, message: str) -> CompilationError:
    return CompilationError(position(node) + message)


# ------------------------------------------------------------
# Evaluation of known expressions
# ------------------------------------------------------------
# Used for the declarations here, and for the known parts of the
# constraints during expansion. The expression has already been checked:
# its type is right and it is known, only values can still be wrong.

def check_index(node, name: str, number: int, value, dim: Values) -> None:
    if value not in dim.values:
        raise error(
            node,
            f"l'indice {number} de '{name}' vaut {value}, hors de {dim.describe()}",
        )


def evaluate(expr, symbols: dict, env: dict):
    """Value of a known expression; env maps loop indices to their values."""
    if isinstance(expr, IntLit):
        return expr.value
    if isinstance(expr, Var):
        if expr.name in env:
            return env[expr.name]
        symbol = symbols[expr.name]
        if isinstance(symbol, EnumValueSymbol):
            return symbol.value
        return symbol.values[()]
    if isinstance(expr, Access):
        symbol = symbols[expr.name]
        key = []
        for number, (index, dim) in enumerate(zip(expr.indices, symbol.dims), 1):
            value = evaluate(index, symbols, env)
            check_index(expr, expr.name, number, value, dim)
            key.append(value)
        return symbol.values[tuple(key)]
    if isinstance(expr, Neg):
        return -evaluate(expr.expr, symbols, env)
    if isinstance(expr, BinOp):
        left = evaluate(expr.left, symbols, env)
        right = evaluate(expr.right, symbols, env)
        return {"+": left + right, "-": left - right, "*": left * right}[expr.op]
    if isinstance(expr, Call):      # abs, the only function on known values
        return abs(evaluate(expr.args[0], symbols, env))
    if isinstance(expr, Compare):
        return compare_values(
            expr.op, evaluate(expr.left, symbols, env), evaluate(expr.right, symbols, env)
        )
    # Connectives are evaluated lazily: a false premise protects the rest.
    if isinstance(expr, Not):
        return not evaluate(expr.expr, symbols, env)
    if isinstance(expr, And):
        return evaluate(expr.left, symbols, env) and evaluate(expr.right, symbols, env)
    if isinstance(expr, Or):
        return evaluate(expr.left, symbols, env) or evaluate(expr.right, symbols, env)
    if isinstance(expr, Implies):
        return not evaluate(expr.left, symbols, env) or evaluate(expr.right, symbols, env)
    raise TypeError(f"evaluate: unexpected node {expr!r}")


def order_key(value):
    return value.index if isinstance(value, EnumValue) else value


def compare_values(op: str, left, right) -> bool:
    a, b = order_key(left), order_key(right)
    return {"=": a == b, "!=": a != b, "<": a < b,
            "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def range_values(low: int, high: int) -> Values:
    return Values(INT, tuple(range(low, high + 1)))


# ------------------------------------------------------------
# Type checking
# ------------------------------------------------------------

class _Checker:
    def __init__(self):
        self.symbols: dict = {}

    def lookup(self, node, name: str, scope: dict):
        if name in scope:
            return scope[name]
        if name in self.symbols:
            return self.symbols[name]
        raise error(node, f"nom non déclaré : {name}")

    def declare(self, node, name: str, symbol, scope: dict | None = None) -> None:
        if name in self.symbols or (scope is not None and name in scope):
            raise error(node, f"déclaration en double : {name}")
        if scope is None:
            self.symbols[name] = symbol
        else:
            scope[name] = symbol

    # ---- expressions: return (type, known) ----

    def check(self, expr, scope: dict, slice_allowed: bool = False) -> tuple[Type, bool]:
        """Type of ``expr`` and whether it is known. scope maps loop indices
        to their type."""
        if isinstance(expr, IntLit):
            return INT, True

        if isinstance(expr, Var):
            symbol = self.lookup(expr, expr.name, scope)
            if isinstance(symbol, Type):                # loop index
                return symbol, True
            if isinstance(symbol, EnumValueSymbol):
                return Type("enum", symbol.value.type), True
            if isinstance(symbol, ConstSymbol) and not symbol.dims:
                return symbol.type, True
            if isinstance(symbol, VarSymbol) and not symbol.dims:
                return symbol.domain.type, False
            if isinstance(symbol, EnumSymbol):
                raise error(expr, f"'{expr.name}' est un type, pas une valeur")
            raise error(expr, f"le tableau '{expr.name}' doit être indicé")

        if isinstance(expr, Access):
            return self.check_access(expr, scope, slice_allowed)

        if isinstance(expr, Star):
            raise error(expr, "'*' n'est permis que comme indice d'une tranche")

        if isinstance(expr, (Neg, BinOp)):
            operands = [expr.expr] if isinstance(expr, Neg) else [expr.left, expr.right]
            for operand in operands:
                self.expect(operand, INT, scope, "l'arithmétique")
                if not self.check(operand, scope)[1]:
                    raise error(
                        operand,
                        "l'arithmétique ne porte que sur des valeurs connues "
                        "à la compilation, pas sur des variables",
                    )
            return INT, True

        if isinstance(expr, Compare):
            left, left_known = self.check(expr.left, scope)
            right, right_known = self.check(expr.right, scope)
            if left != right:
                raise error(expr, f"comparaison entre {left} et {right}")
            if left == BOOL and expr.op not in ("=", "!="):
                raise error(expr, f"'{expr.op}' ne s'applique pas aux booléens")
            return BOOL, left_known and right_known

        if isinstance(expr, Not):
            return BOOL, self.expect(expr.expr, BOOL, scope, "'not'")
        if isinstance(expr, (And, Or, Implies)):
            name = {And: "'and'", Or: "'or'", Implies: "'->'"}[type(expr)]
            left = self.expect(expr.left, BOOL, scope, name)
            right = self.expect(expr.right, BOOL, scope, name)
            return BOOL, left and right

        if isinstance(expr, Call):
            return self.check_call(expr, scope)

        raise error(expr, "expression inattendue")

    def expect(self, expr, expected: Type, scope: dict, where: str) -> bool:
        """Checks that ``expr`` has the type ``expected``; returns known."""
        actual, known = self.check(expr, scope)
        if actual != expected:
            raise error(expr, f"{where} attend un {expected}, pas un {actual}")
        return known

    def check_known(self, expr, scope: dict, what: str) -> Type:
        actual, known = self.check(expr, scope)
        if not known:
            raise error(expr, f"{what} doit être une valeur connue à la compilation")
        return actual

    def check_access(self, expr: Access, scope: dict, slice_allowed: bool):
        symbol = self.lookup(expr, expr.name, scope)
        if not isinstance(symbol, (ConstSymbol, VarSymbol)) or not symbol.dims:
            raise error(expr, f"'{expr.name}' n'est pas un tableau")
        if len(expr.indices) != len(symbol.dims):
            raise error(
                expr,
                f"'{expr.name}' attend {len(symbol.dims)} indice(s), "
                f"{len(expr.indices)} donné(s)",
            )
        for number, (index, dim) in enumerate(zip(expr.indices, symbol.dims), 1):
            if isinstance(index, Star):
                if not slice_allowed:
                    raise error(
                        expr,
                        "une tranche n'est permise qu'en argument d'une contrainte globale",
                    )
                continue
            actual = self.check_known(index, scope, f"l'indice {number} de '{expr.name}'")
            if actual != dim.type:
                raise error(
                    index,
                    f"l'indice {number} de '{expr.name}' doit être un {dim.type}, "
                    f"pas un {actual}",
                )
        if isinstance(symbol, ConstSymbol):
            return symbol.type, True
        return symbol.domain.type, False

    def check_call(self, expr: Call, scope: dict):
        if expr.name == "abs":
            if len(expr.args) != 1:
                raise error(expr, f"abs attend 1 argument, {len(expr.args)} donné(s)")
            self.expect(expr.args[0], INT, scope, "abs")
            self.check_known(expr.args[0], scope, "l'argument de abs")
            return INT, True
        if expr.name not in GLOBALS:
            raise error(expr, f"fonction inconnue : {expr.name}")
        if not expr.args:
            raise error(expr, f"{expr.name} attend au moins un argument")
        types, known = [], True
        for arg in expr.args:
            actual, arg_known = self.check(arg, scope, slice_allowed=True)
            types.append((arg, actual))
            known = known and arg_known
        if expr.name == "allDifferent":
            first = types[0][1]
            for arg, actual in types:
                if actual == BOOL:
                    raise error(arg, "allDifferent porte sur des entiers ou des énumérés")
                if actual != first:
                    raise error(arg, f"allDifferent mélange {first} et {actual}")
        else:
            for arg, actual in types:
                if actual != BOOL:
                    raise error(arg, f"{expr.name} attend des booléens, pas un {actual}")
        return BOOL, known

    # ---- declarations ----

    def values_of(self, domain, scope: dict, env: dict) -> Values:
        """The values of a domain (bool, a..b or an enum type)."""
        if isinstance(domain, EnumDomain):
            if domain.name == "bool":
                return Values(BOOL, (False, True))
            symbol = self.lookup(domain, domain.name, scope)
            if not isinstance(symbol, EnumSymbol):
                raise error(domain, f"'{domain.name}' n'est pas un type énuméré")
            return symbol.values
        bounds = []
        for bound in (domain.low, domain.high):
            actual = self.check_known(bound, scope, "une borne d'intervalle")
            if actual != INT:
                raise error(bound, f"une borne d'intervalle doit être un entier, pas un {actual}")
            bounds.append(evaluate(bound, self.symbols, env))
        low, high = bounds
        if low > high:
            raise error(domain, f"domaine vide : {low}..{high}")
        return range_values(low, high)

    def dimension(self, size) -> Values:
        """An array size: an enum type name, or a known integer >= 1."""
        if isinstance(size, Var) and isinstance(self.symbols.get(size.name), EnumSymbol):
            return self.symbols[size.name].values
        actual = self.check_known(size, {}, "la taille d'un tableau")
        if actual != INT:
            raise error(size, f"la taille d'un tableau doit être un entier, pas un {actual}")
        n = evaluate(size, self.symbols, {})
        if n < 1:
            raise error(size, f"la taille d'un tableau doit être au moins 1, pas {n}")
        return range_values(1, n)

    def declare_const(self, decl: ConstDecl) -> None:
        if not decl.dims:
            # The grammar only allows an arithmetic expression here: the value
            # is an integer or an enum value, never a boolean.
            actual = self.check_known(decl.value, {}, "la valeur d'une constante")
            value = evaluate(decl.value, self.symbols, {})
            self.declare(decl, decl.name, ConstSymbol(decl.name, actual, [], {(): value}))
            return
        dims = [self.dimension(size) for size in decl.dims]
        values: dict = {}
        types: set = set()

        def fill(literal, depth: int, key: tuple) -> None:
            dim = dims[depth]
            if not isinstance(literal, ArrayLiteral) or len(literal.elements) != len(dim.values):
                raise error(
                    literal,
                    f"'{decl.name}' : la dimension {depth + 1} doit contenir "
                    f"{len(dim.values)} élément(s)",
                )
            for index, element in zip(dim.values, literal.elements):
                if depth + 1 < len(dims):
                    fill(element, depth + 1, key + (index,))
                    continue
                if isinstance(element, ArrayLiteral):
                    raise error(element, f"'{decl.name}' a trop de dimensions")
                actual = self.check_known(element, {}, "un élément de tableau constant")
                if actual == BOOL:
                    raise error(element, "un tableau constant contient des entiers ou des énumérés")
                types.add(actual)
                if len(types) > 1:
                    raise error(element, f"'{decl.name}' mélange des valeurs de types différents")
                values[key + (index,)] = evaluate(element, self.symbols, {})

        fill(decl.value, 0, ())
        self.declare(decl, decl.name, ConstSymbol(decl.name, types.pop(), dims, values))

    def declare_enum(self, decl: EnumDecl) -> None:
        values = tuple(EnumValue(decl.name, i, name) for i, name in enumerate(decl.values))
        self.declare(decl, decl.name, EnumSymbol(decl.name, Values(Type("enum", decl.name), values)))
        for value in values:
            self.declare(decl, value.name, EnumValueSymbol(value))

    # ---- statements of the body ----

    def check_statement(self, statement, scope: dict) -> None:
        if isinstance(statement, Constraint):
            self.expect(statement.expr, BOOL, scope, "une contrainte")
            return
        inner = dict(scope)
        for iterator in statement.iterators:
            if isinstance(iterator.domain, EnumDomain):
                symbol = self.lookup(iterator.domain, iterator.domain.name, inner)
                if not isinstance(symbol, EnumSymbol):
                    raise error(iterator.domain, f"'{iterator.domain.name}' n'est pas un type énuméré")
                index_type = symbol.values.type
            else:
                for bound in (iterator.domain.low, iterator.domain.high):
                    actual = self.check_known(bound, inner, "une borne d'intervalle")
                    if actual != INT:
                        raise error(bound, f"une borne d'intervalle doit être un entier, pas un {actual}")
                index_type = INT
            self.declare(iterator, iterator.name, index_type, inner)
        for nested in statement.body:
            self.check_statement(nested, inner)


def analyse(program: Program) -> Model:
    """Builds the symbol table of ``program`` and checks its constraints."""
    checker = _Checker()
    variables, statements = [], []
    for statement in program.statements:
        if isinstance(statement, ConstDecl):
            checker.declare_const(statement)
        elif isinstance(statement, EnumDecl):
            checker.declare_enum(statement)
        elif isinstance(statement, (VarDecl, ArrayDecl)):
            dims = [checker.dimension(size) for size in getattr(statement, "dims", [])]
            domain = checker.values_of(statement.domain, {}, {})
            symbol = VarSymbol(statement.name, dims, domain)
            checker.declare(statement, statement.name, symbol)
            variables.append(symbol)
        else:
            statements.append(statement)
    # Constraints may use names declared after them: they are checked once
    # every declaration is known.
    for statement in statements:
        checker.check_statement(statement, {})
    return Model(checker.symbols, variables, statements)


def cells(variable: VarSymbol) -> list[tuple]:
    """The index tuples of a variable, row by row; [()] for a scalar."""
    return list(product(*(dim.values for dim in variable.dims)))
