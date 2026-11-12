"""Question 3, transformation: unrolled and simplified constraints.

    Model (semantics.py) --expand()--> Expansion: constraints without loops

Every forall is replaced by its instances, the known parts are computed and
the connectives with a known operand are simplified, lazily: in
``i < N -> grid[i + 1][1] != grid[i][1]`` the right side is never looked at
when ``i < N`` is false, so grid[N + 1] raises no error.

The result is a list of formulas made of:

- ``Cell(name, indices)``: one cell of a variable, e.g. grid[1][2], or x;
- known values: Python ints, bools and ``EnumValue``;
- ``Compare`` between a cell and a value or between two cells;
- ``Not``, ``And``, ``Or``, ``Implies`` and global constraints ``Call``,
  whose arguments are cells, values or formulas.

Comparisons are normalised to reduce the cases left to the CNF translation:
a cell compared with a value is on the left (3 < x becomes x > 3), two
cells are only compared with = != < <= (x > y becomes y < x), and a negated
comparison is replaced by the opposite one (not x = 2 becomes x != 2).
"""

from dataclasses import dataclass
from itertools import product

from semantics import (
    EnumValue,
    Model,
    VarSymbol,
    check_index,
    compare_values,
    evaluate,
    order_key,
)
from syntax import (
    Access,
    And,
    BinOp,
    Call,
    Compare,
    Constraint,
    EnumDomain,
    Implies,
    IntLit,
    Neg,
    Not,
    Or,
    Star,
    Var,
    position,
)


@dataclass(frozen=True)
class Cell:
    """One cell of a variable: grid[1][2] is Cell("grid", (1, 2))."""
    name: str
    indices: tuple = ()

    def __str__(self) -> str:
        return self.name + "".join(f"[{index}]" for index in self.indices)


@dataclass
class Expansion:
    constraints: list   # formulas; False makes the model unsatisfiable
    warnings: list      # messages, e.g. a constraint that is always false


MIRROR = {"=": "=", "!=": "!=", "<": ">", "<=": ">=", ">": "<", ">=": "<="}
NEGATION = {"=": "!=", "!=": "=", "<": ">=", "<=": ">", ">": "<=", ">=": "<"}


def is_value(term) -> bool:
    return isinstance(term, (bool, int, EnumValue))


def make_compare(op: str, left, right):
    """A normalised comparison, or its value when both sides are known."""
    if is_value(left) and is_value(right):
        return compare_values(op, left, right)
    if is_value(left):                      # value on the right
        op, left, right = MIRROR[op], right, left
    if isinstance(right, bool):             # b = true is b, b != true is not b
        positive = (op == "=") == right
        return left if positive else make_not(left)
    if not is_value(right) and op in (">", ">="):
        op, left, right = MIRROR[op], right, left
    return Compare(op, left, right)


def make_not(formula):
    if isinstance(formula, bool):
        return not formula
    if isinstance(formula, Not):
        return formula.expr
    if isinstance(formula, Compare):
        return make_compare(NEGATION[formula.op], formula.left, formula.right)
    return Not(formula)


class _Expander:
    def __init__(self, model: Model):
        self.model = model
        self.symbols = model.symbols

    # ---- statements ----

    def statement(self, statement, env: dict, out: list, warnings: list) -> None:
        if isinstance(statement, Constraint):
            formula = self.formula(statement.expr, env)
            if formula is True:
                return
            if formula is False:
                where = ", ".join(f"{k} = {v}" for k, v in env.items())
                warnings.append(
                    f"{position(statement)}contrainte toujours fausse"
                    + (f" (pour {where})" if where else "")
                    + " : le modèle est insatisfiable"
                )
            out.append(formula)
            return
        self.unroll(statement, 0, env, out, warnings)

    def unroll(self, loop, number: int, env: dict, out: list, warnings: list) -> None:
        """Instances of the iterators number, number + 1, ... of the loop."""
        if number == len(loop.iterators):
            for nested in loop.body:
                self.statement(nested, env, out, warnings)
            return
        iterator = loop.iterators[number]
        domain = iterator.domain
        if isinstance(domain, EnumDomain):
            values = self.symbols[domain.name].values.values
        else:
            low = evaluate(domain.low, self.symbols, env)
            high = evaluate(domain.high, self.symbols, env)
            values = range(low, high + 1)       # empty when low > high
        for value in values:
            self.unroll(loop, number + 1, {**env, iterator.name: value}, out, warnings)

    # ---- expressions ----

    def term(self, expr, env: dict):
        """A value, a Cell or a formula equivalent to ``expr``."""
        if isinstance(expr, (IntLit, Neg, BinOp)):
            return evaluate(expr, self.symbols, env)
        if isinstance(expr, Var):
            symbol = self.symbols.get(expr.name)
            if expr.name not in env and isinstance(symbol, VarSymbol):
                return Cell(expr.name)
            return evaluate(expr, self.symbols, env)
        if isinstance(expr, Access):
            symbol = self.symbols[expr.name]
            if not isinstance(symbol, VarSymbol):
                return evaluate(expr, self.symbols, env)
            return Cell(expr.name, self.indices(expr, symbol, env))
        if isinstance(expr, Call) and expr.name == "abs":
            return evaluate(expr, self.symbols, env)
        return self.formula(expr, env)

    def indices(self, expr: Access, symbol, env: dict) -> tuple:
        key = []
        for number, (index, dim) in enumerate(zip(expr.indices, symbol.dims), 1):
            value = evaluate(index, self.symbols, env)
            check_index(expr, expr.name, number, value, dim)
            key.append(value)
        return tuple(key)

    def formula(self, expr, env: dict):
        """True, False or a formula on cells equivalent to ``expr``."""
        if isinstance(expr, Compare):
            return make_compare(expr.op, self.term(expr.left, env), self.term(expr.right, env))
        if isinstance(expr, Not):
            return make_not(self.formula(expr.expr, env))
        if isinstance(expr, And):
            left = self.formula(expr.left, env)
            if left is False:
                return False                    # the right side is not evaluated
            right = self.formula(expr.right, env)
            if left is True or right is False:
                return right
            return left if right is True else And(left, right)
        if isinstance(expr, Or):
            left = self.formula(expr.left, env)
            if left is True:
                return True
            right = self.formula(expr.right, env)
            if left is False or right is True:
                return right
            return left if right is False else Or(left, right)
        if isinstance(expr, Implies):
            left = self.formula(expr.left, env)
            if left is False:
                return True                     # the right side is not evaluated
            right = self.formula(expr.right, env)
            if left is True:
                return right
            if right is True:
                return True
            return make_not(left) if right is False else Implies(left, right)
        if isinstance(expr, Call):
            return self.global_constraint(expr, env)
        return self.term(expr, env)             # a boolean cell or value

    def arguments(self, call: Call, env: dict) -> list:
        """Arguments of a global constraint, slices replaced by their cells."""
        result = []
        for arg in call.args:
            if not (isinstance(arg, Access) and any(isinstance(i, Star) for i in arg.indices)):
                result.append(self.term(arg, env))
                continue
            symbol = self.symbols[arg.name]
            choices = []
            for number, (index, dim) in enumerate(zip(arg.indices, symbol.dims), 1):
                if isinstance(index, Star):
                    choices.append(dim.values)
                else:
                    value = evaluate(index, self.symbols, env)
                    check_index(arg, arg.name, number, value, dim)
                    choices.append((value,))
            for key in product(*choices):       # row by row
                if isinstance(symbol, VarSymbol):
                    result.append(Cell(arg.name, key))
                else:
                    result.append(symbol.values[key])
        return result

    def global_constraint(self, call: Call, env: dict):
        args = self.arguments(call, env)
        if call.name == "allDifferent":
            known = [order_key(a) for a in args if is_value(a)]
            if len(known) != len(set(known)):
                return False
            if len(args) - len(known) == 0 or len(args) < 2:
                return True
            return Call("allDifferent", args)
        true_count = sum(1 for a in args if a is True)
        unknown = [a for a in args if not isinstance(a, bool)]
        if call.name == "atLeastOne":
            if true_count:
                return True
            if not unknown:
                return False
            return unknown[0] if len(unknown) == 1 else Call("atLeastOne", unknown)
        # atMostOne and exactlyOne
        if true_count >= 2:
            return False
        if true_count == 1:                     # every other argument is false
            return conjunction([make_not(a) for a in unknown])
        if call.name == "atMostOne":
            return True if len(unknown) <= 1 else Call("atMostOne", unknown)
        if not unknown:
            return False
        return unknown[0] if len(unknown) == 1 else Call("exactlyOne", unknown)


def conjunction(formulas: list):
    result = True
    for formula in formulas:
        result = formula if result is True else And(result, formula)
    return result


def expand(model: Model) -> Expansion:
    """Unrolls the loops of ``model`` and simplifies its constraints."""
    expander = _Expander(model)
    constraints, warnings = [], []
    for statement in model.statements:
        expander.statement(statement, {}, constraints, warnings)
    return Expansion(constraints, warnings)


def show(formula) -> str:
    """Readable text of an expanded formula, fully parenthesised."""
    if isinstance(formula, bool):
        return "true" if formula else "false"
    if isinstance(formula, (int, EnumValue, Cell)):
        return str(formula)
    if isinstance(formula, Compare):
        return f"{show(formula.left)} {formula.op} {show(formula.right)}"
    if isinstance(formula, Not):
        inner = show(formula.expr)
        return f"not ({inner})" if isinstance(formula.expr, Compare) else f"not {inner}"
    if isinstance(formula, (And, Or, Implies)):
        op = {And: "and", Or: "or", Implies: "->"}[type(formula)]
        return f"({show(formula.left)} {op} {show(formula.right)})"
    if isinstance(formula, Call):
        return f"{formula.name}({', '.join(show(a) for a in formula.args)})"
    raise TypeError(f"show: unexpected formula {formula!r}")

