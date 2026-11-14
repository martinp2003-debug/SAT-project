"""Orchestration réutilisable de la compilation et de la résolution CSP."""

from pathlib import Path
import sys

from encoding import decode, encode
from expansion import expand
from semantics import analyse


# La compilation reste indépendante du solveur ; seule cette couche d'exécution
# connaît l'implémentation DPLL de la partie I.
PART_1 = Path(__file__).resolve().parent.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question2.sat import verifier_valuation  # noqa: E402
from question6.solver import dpll_optimized  # noqa: E402


def prepare_program(program):
    """Analyse et développe un programme CSP déjà parsé."""
    model = analyse(program)
    expanded = expand(model)
    return model, expanded


def compile_program(program, amo: str = "pairwise"):
    """Analyse, développe et encode un programme CSP déjà parsé."""
    model, expanded = prepare_program(program)
    return model, expanded, encode(model, expanded, amo)


def solve_encoding(encoding):
    """Résout une FNC encodée et décode ses variables nommées."""
    formula = [frozenset(clause) for clause in encoding.clauses]
    satisfiable, valuation = dpll_optimized(formula, encoding.variable_count)
    if not satisfiable:
        return False, None
    if valuation is None or not verifier_valuation(formula, valuation):
        raise RuntimeError("La valuation calculée ne satisfait pas la FNC.")
    return True, decode(encoding, valuation)
