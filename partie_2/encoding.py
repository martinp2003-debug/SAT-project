"""Question 4: translation of the expanded constraints into CNF.

    Expansion (expansion.py) --encode()--> Encoding: DIMACS clauses + mapping

Direct encoding of the domains. A variable x of domain {v1, ..., vk} gets
one SAT variable x_v per value, x_v meaning "x = v", with the clauses of
exactlyOne(x_v1, ..., x_vk): one clause x_v1 or ... or x_vk, and for
each pair i < j the clause not x_vi or not x_vj. A bool variable stays a
single SAT variable. Enum values are ordered by their declaration.

Each expanded constraint becomes a formula on these SAT variables (cnf.py),
then clauses. The choices for the comparisons, with x, y of domains Dx, Dy:

- x = v is x_v, x != v is not x_v (false / true when v is not in Dx);
- x < v (and <=, >, >=): the values of Dx that satisfy the comparison,
  either as a disjunction "x takes a good value" or as a conjunction "x
  takes no bad value". Thanks to exactlyOne both are equivalent; we keep
  the one with fewer literals. At the top level the disjunction is one
  clause, the conjunction unit clauses: both need no auxiliary variable;
- x = y: for each v of Dx, x_v -> y_v (|Dx| binary clauses);
- x != y: for each v of Dx and Dy, not (x_v and y_v) (binary clauses);
- x < y: for each v of Dx, x_v -> (y_w for some w > v in Dy), one clause
  per value of x, without auxiliary variables; x <= y in the same way.

Global constraints: atLeastOne is a disjunction, atMostOne the pairwise
encoding (n(n-1)/2 binary clauses), exactlyOne both; allDifferent says that,
for each value v, at most one of the expressions equals v.

Sinz's sequential counter (option amo="sinz") encodes atMostOne with 3n - 4
clauses and n - 1 auxiliary variables. Its clauses only mean "at most one"
for well chosen auxiliaries: a model of them exists exactly when at most one
x_i is true, but they do not define a literal equivalent to atMostOne. It is
therefore only used where the constraint must hold (a domain, or a whole
constraint), never inside a formula, where it could be negated, as in
b -> not atMostOne(...): there the pairwise encoding is used.
"""

from dataclasses import dataclass, field
from itertools import combinations

from cnf import land, liff, lnot, lor, to_clauses
from expansion import Cell, Expansion
from semantics import BOOL, Model, cells, compare_values, order_key
from syntax import And, Call, Compare, Implies, Not, Or


@dataclass
class Encoding:
    """The CNF of a model and the mapping between cells and SAT variables."""
    variable_count: int = 0
    clauses: list = field(default_factory=list)
    id_to_name: dict = field(default_factory=dict)    # named SAT variables
    cells: dict = field(default_factory=dict)         # Cell -> {value: id}
    domains: dict = field(default_factory=dict)       # Cell -> Values


class _Encoder:
    def __init__(self, model: Model, amo: str):
        if amo not in ("pairwise", "sinz"):
            raise ValueError(f"encodage de atMostOne inconnu : {amo}")
        self.amo = amo
        self.result = Encoding()

    def fresh(self, name: str | None = None) -> int:
        self.result.variable_count += 1
        identifier = self.result.variable_count
        if name is not None:
            self.result.id_to_name[identifier] = name
        return identifier

    # ---- domains ----

    def declare(self, model: Model) -> None:
        """One SAT variable per bool cell, one per value of the other cells."""
        for variable in model.variables:
            for key in cells(variable):
                cell = Cell(variable.name, key)
                self.result.domains[cell] = variable.domain
                if variable.domain.type == BOOL:
                    self.result.cells[cell] = {True: self.fresh(str(cell))}
                    continue
                ids = {v: self.fresh(f"{cell}={v}") for v in variable.domain.values}
                self.result.cells[cell] = ids
                self.exactly_one_clauses(list(ids.values()))

    def value_literal(self, cell: Cell, value):
        """The formula "cell = value": a literal, or False out of the domain."""
        return self.result.cells[cell].get(value, False)

    # ---- formulas ----

    def formula(self, item):
        """Propositional formula (cnf.py) equivalent to an expanded formula."""
        if isinstance(item, bool):
            return item
        if isinstance(item, Cell):                      # a bool cell
            return self.result.cells[item][True]
        if isinstance(item, Not):
            return lnot(self.formula(item.expr))
        if isinstance(item, And):
            return land([self.formula(item.left), self.formula(item.right)])
        if isinstance(item, Or):
            return lor([self.formula(item.left), self.formula(item.right)])
        if isinstance(item, Implies):
            return lor([lnot(self.formula(item.left)), self.formula(item.right)])
        if isinstance(item, Compare):
            return self.compare(item)
        if isinstance(item, Call):
            return self.global_formula(item)
        raise TypeError(f"formule inattendue : {item!r}")

    def is_bool_term(self, term) -> bool:
        return not isinstance(term, Cell) or self.result.domains[term].type == BOOL

    def compare(self, item: Compare):
        op, left, right = item.op, item.left, item.right
        if self.is_bool_term(left):                     # = or != on formulas
            same = liff(self.formula(left), self.formula(right))
            return same if op == "=" else lnot(same)
        domain = self.result.domains[left].values
        if not isinstance(right, Cell):                 # a cell and a value
            if op == "=":
                return self.value_literal(left, right)
            if op == "!=":
                return lnot(self.value_literal(left, right))
            good = [v for v in domain if compare_values(op, v, right)]
            bad = [v for v in domain if v not in good]
            if len(good) <= len(bad):
                return lor([self.value_literal(left, v) for v in good])
            return land([lnot(self.value_literal(left, v)) for v in bad])
        # two cells, op is one of = != < <= (see expansion.py)
        other = self.result.domains[right].values
        if op == "!=":
            return land([
                lor([lnot(self.value_literal(left, v)), lnot(self.value_literal(right, v))])
                for v in domain if v in other
            ])
        clauses = []
        for v in domain:
            if op == "=":
                allowed = [v] if v in other else []
            else:
                allowed = [w for w in other if compare_values(op, v, w)]
            clauses.append(lor(
                [lnot(self.value_literal(left, v))]
                + [self.value_literal(right, w) for w in allowed]
            ))
        return land(clauses)

    def equals_terms(self, terms: list) -> list[list]:
        """For allDifferent: for each value, the formulas "term = value"."""
        values = {}
        for term in terms:
            if isinstance(term, Cell):
                for v in self.result.domains[term].values:
                    values.setdefault(order_key(v), [])
            else:
                values.setdefault(order_key(term), [])
        for term in terms:
            for key, formulas in values.items():
                if isinstance(term, Cell):
                    match = [v for v in self.result.cells[term] if order_key(v) == key]
                    formulas.append(self.value_literal(term, match[0]) if match else False)
                else:
                    formulas.append(order_key(term) == key)
        return list(values.values())

    def global_formula(self, item: Call):
        if item.name == "allDifferent":
            return land([at_most_one_pairwise(f) for f in self.equals_terms(item.args)])
        formulas = [self.formula(arg) for arg in item.args]
        if item.name == "atLeastOne":
            return lor(formulas)
        if item.name == "atMostOne":
            return at_most_one_pairwise(formulas)
        return land([lor(formulas), at_most_one_pairwise(formulas)])   # exactlyOne

    # ---- clauses ----

    def add(self, formula) -> None:
        self.result.clauses.extend(to_clauses(formula, self.fresh))

    def at_most_one_clauses(self, literals: list) -> None:
        """atMostOne on literals that must hold: pairwise or Sinz."""
        if self.amo == "pairwise" or len(literals) <= 2:
            self.add(at_most_one_pairwise(literals))
            return
        self.result.clauses.extend(sinz(literals, self.fresh))

    def exactly_one_clauses(self, literals: list) -> None:
        self.add(lor(literals))
        self.at_most_one_clauses(literals)

    def constraint(self, item) -> None:
        """Clauses of an expanded constraint, which must hold."""
        cardinality = ("atMostOne", "exactlyOne", "allDifferent")
        if self.amo == "sinz" and isinstance(item, Call) and item.name in cardinality:
            if item.name == "allDifferent":
                groups = self.equals_terms(item.args)
            else:
                groups = [[self.formula(arg) for arg in item.args]]
                if item.name == "exactlyOne":
                    self.add(lor(groups[0]))
            for group in groups:
                self.at_most_one_clauses(self.as_literals(group))
            return
        self.add(self.formula(item))

    def as_literals(self, formulas: list) -> list[int]:
        """Literals for formulas (an auxiliary for a compound one). A known
        true formula becomes a literal forced to true."""
        literals = []
        for formula in formulas:
            if formula is False:
                continue
            if isinstance(formula, int) and not isinstance(formula, bool):
                literals.append(formula)
                continue
            auxiliary = self.fresh()
            self.add(liff(auxiliary, formula))      # a full definition
            literals.append(auxiliary)
        return literals


def at_most_one_pairwise(formulas: list):
    """not (a and b) for each pair: n(n-1)/2 binary clauses at the top level."""
    formulas = [f for f in formulas if f is not False]
    return land([lor([lnot(a), lnot(b)]) for a, b in combinations(formulas, 2)])


def sinz(literals: list[int], fresh) -> list[list[int]]:
    """Sinz's sequential counter for atMostOne(x1, ..., xn), n >= 2.

    s_i means "one of x1..xi is true": n - 1 auxiliaries, 3n - 4 clauses.
    """
    n = len(literals)
    s = [fresh() for _ in range(n - 1)]
    x = literals
    clauses = [[-x[0], s[0]]]
    for i in range(1, n - 1):
        clauses += [[-x[i], s[i]], [-s[i - 1], s[i]], [-x[i], -s[i - 1]]]
    clauses.append([-x[n - 1], -s[n - 2]])
    return clauses


def encode(model: Model, expansion: Expansion, amo: str = "pairwise") -> Encoding:
    """CNF of the expanded constraints of ``model``, with the domain clauses."""
    encoder = _Encoder(model, amo)
    encoder.declare(model)
    for constraint in expansion.constraints:
        encoder.constraint(constraint)
    return encoder.result


def decode(encoding: Encoding, valuation: dict[int, bool]) -> dict:
    """The value of each cell, from a (possibly partial) SAT valuation."""
    values = {}
    for cell, ids in encoding.cells.items():
        if encoding.domains[cell].type == BOOL:
            values[cell] = valuation.get(ids[True], False)
        else:
            chosen = [v for v, identifier in ids.items() if valuation.get(identifier, False)]
            if len(chosen) != 1:
                raise RuntimeError(f"{cell} n'a pas exactement une valeur : {chosen}")
            values[cell] = chosen[0]
    return values
