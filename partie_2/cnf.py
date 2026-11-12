"""Question 4, last step: propositional formulas on DIMACS literals to CNF.

A formula is True, False, a DIMACS literal (a non-zero int), or a node
PAnd, POr, PNot, PIff. The constructors land(), lor(), lnot() and liff()
simplify constants and flatten nested and/or, so that the encoding of
question 4 can build formulas without caring about these cases.

to_clauses() first pushes the negations down to the literals (negation
normal form). In this form every subformula occurs positively, so the
Tseitin transformation only needs one direction of each definition
(Plaisted-Greenbaum): an auxiliary t for a subformula G only gets the
clauses of t -> G. The CNF is satisfiable if and only if the formula is,
and every model of the CNF, restricted to the named variables, is a model
of the formula.

No auxiliary variable is created when it is not needed: a conjunction gives
the clauses of its members, and a disjunction of literals is a clause, so
that x -> y or not (a and b) gives one clause each, as the subject suggests.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PAnd:
    items: tuple


@dataclass(frozen=True)
class POr:
    items: tuple


@dataclass(frozen=True)
class PNot:
    item: object


@dataclass(frozen=True)
class PIff:
    left: object
    right: object


def land(items) -> object:
    flat = []
    for item in items:
        if item is False:
            return False
        if item is True:
            continue
        flat.extend(item.items if isinstance(item, PAnd) else [item])
    if not flat:
        return True
    return flat[0] if len(flat) == 1 else PAnd(tuple(flat))


def lor(items) -> object:
    flat = []
    for item in items:
        if item is True:
            return True
        if item is False:
            continue
        flat.extend(item.items if isinstance(item, POr) else [item])
    if not flat:
        return False
    return flat[0] if len(flat) == 1 else POr(tuple(flat))


def lnot(item) -> object:
    if isinstance(item, bool):
        return not item
    if isinstance(item, int):
        return -item
    if isinstance(item, PNot):
        return item.item
    return PNot(item)


def liff(left, right) -> object:
    if isinstance(left, bool):
        return right if left else lnot(right)
    if isinstance(right, bool):
        return left if right else lnot(left)
    return PIff(left, right)


def nnf(formula, positive: bool = True) -> object:
    """Negation normal form: PNot and PIff disappear, only literals are negated."""
    if isinstance(formula, bool):
        return formula if positive else not formula
    if isinstance(formula, int):
        return formula if positive else -formula
    if isinstance(formula, PNot):
        return nnf(formula.item, not positive)
    if isinstance(formula, PIff):
        # a <-> b  is  (a and b) or (not a and not b); negated, b is negated
        a, b = formula.left, formula.right if positive else lnot(formula.right)
        return lor([land([nnf(a), nnf(b)]), land([nnf(a, False), nnf(b, False)])])
    items = [nnf(item, positive) for item in formula.items]
    is_and = isinstance(formula, PAnd) == positive      # De Morgan
    return land(items) if is_and else lor(items)


def to_clauses(formula, fresh: Callable[[], int]) -> list[list[int]]:
    """Clauses equisatisfiable with ``formula``; fresh() gives a new variable."""
    clauses: list[list[int]] = []

    def literal(item) -> int:
        """A literal that implies ``item`` (an auxiliary for a conjunction)."""
        if isinstance(item, int):
            return item
        auxiliary = fresh()
        implied(auxiliary, item)
        return auxiliary

    def implied(premise: int | None, item) -> None:
        """Clauses of premise -> item (of item alone if premise is None)."""
        prefix = [] if premise is None else [-premise]
        if isinstance(item, PAnd):
            for member in item.items:
                implied(premise, member)
        elif isinstance(item, POr):
            clauses.append(prefix + [literal(member) for member in item.items])
        else:
            clauses.append(prefix + [item])

    formula = nnf(formula)
    if formula is False:
        return [[]]                 # the empty clause: unsatisfiable
    if formula is not True:
        implied(None, formula)
    return clauses
