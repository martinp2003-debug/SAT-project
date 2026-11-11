"""Compile a propositional constraint model to DIMACS or solve it."""

import argparse
from pathlib import Path
import sys

from lark.exceptions import UnexpectedInput

from compiler import CompilationError, CompilationResult, compile_program
from dimacs import to_dimacs, write_dimacs
from syntax import parse


# Reuse the solver from Part I while keeping compilation independent from it.
PART_1 = Path(__file__).resolve().parent.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question2.sat import dpll_valuation, verifier_valuation  # noqa: E402


def decode_model(
    compilation: CompilationResult, valuation: dict[int, bool]
) -> dict[str, bool]:
    """Restrict a possibly partial SAT valuation to named source variables."""
    return {
        name: valuation.get(identifier, False)
        for name, identifier in compilation.name_to_id.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python csp.py",
        description="Compile a propositional constraint model to SAT",
    )
    parser.add_argument("model", type=Path, help="model file (.csp)")
    parser.add_argument("--dimacs", type=Path, help="write the DIMACS formula")
    parser.add_argument("--solve", action="store_true", help="solve the formula")
    args = parser.parse_args()

    try:
        text = args.model.read_text(encoding="utf-8")
        program = parse(text)
        compilation = compile_program(program)
        dimacs = to_dimacs(compilation)
    except (OSError, UnexpectedInput, CompilationError) as error:
        print(f"{args.model}: {error}", file=sys.stderr)
        return 1

    if args.dimacs is not None:
        try:
            write_dimacs(args.dimacs, compilation)
        except OSError as error:
            print(f"{args.dimacs}: {error}", file=sys.stderr)
            return 1

    if not args.solve:
        if args.dimacs is None:
            print(dimacs, end="")
        return 0

    formula = [frozenset(clause) for clause in compilation.clauses]
    satisfiable, valuation = dpll_valuation(formula)
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable:
        if valuation is None:
            raise RuntimeError("Le solveur SAT n'a pas produit de valuation.")
        if not verifier_valuation(formula, valuation):
            raise RuntimeError("La valuation calculée ne satisfait pas la FNC.")
        for name, value in decode_model(compilation, valuation).items():
            print(f"{name} = {'true' if value else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
