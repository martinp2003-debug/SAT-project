"""Compile a constraint model to DIMACS or solve it.

    text --parse--> AST --analyse--> Model --expand--> constraints
         --encode--> CNF --(DIMACS)--> Part I solver --decode--> values
"""

import argparse
from pathlib import Path
import sys

from lark.exceptions import UnexpectedInput

from diagnostics import CompilationError
from dimacs import to_dimacs, write_dimacs
from encoding import decode, encode
from expansion import expand, show
from semantics import analyse
from syntax import parse, pretty, syntax_error_message


# Reuse the solver from Part I while keeping compilation independent from it.
PART_1 = Path(__file__).resolve().parent.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question2.sat import verifier_valuation  # noqa: E402
from question6.solver import dpll_optimized  # noqa: E402


def show_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python csp.py",
        description="Compile a constraint model to SAT",
    )
    parser.add_argument("model", type=Path, help="model file (.csp)")
    parser.add_argument("--dimacs", type=Path, help="write the DIMACS formula")
    parser.add_argument("--solve", action="store_true", help="solve the formula")
    parser.add_argument("--ast", action="store_true", help="print the syntax tree")
    parser.add_argument(
        "--expand", action="store_true",
        help="print the constraints after unrolling and simplification",
    )
    parser.add_argument(
        "--amo", choices=("pairwise", "sinz"), default="pairwise",
        help="encoding of atMostOne: pairwise (default) or Sinz's counter",
    )
    args = parser.parse_args()

    try:
        text = args.model.read_text(encoding="utf-8")
        program = parse(text)
        if args.ast:
            print(pretty(program))
            return 0
        model = analyse(program)
        expansion = expand(model)
        for warning in expansion.warnings:
            print(f"{args.model}: avertissement : {warning}", file=sys.stderr)
        if args.expand:
            for constraint in expansion.constraints:
                print(show(constraint))
            return 0
        encoding = encode(model, expansion, args.amo)
    except UnexpectedInput as error:
        print(f"{args.model}: {syntax_error_message(error)}", file=sys.stderr)
        return 1
    except (OSError, CompilationError) as error:
        print(f"{args.model}: {error}", file=sys.stderr)
        return 1

    if args.dimacs is not None:
        try:
            write_dimacs(args.dimacs, encoding)
        except OSError as error:
            print(f"{args.dimacs}: {error}", file=sys.stderr)
            return 1

    if not args.solve:
        if args.dimacs is None:
            print(to_dimacs(encoding), end="")
        return 0

    formula = [frozenset(clause) for clause in encoding.clauses]
    satisfiable, valuation = dpll_optimized(formula, encoding.variable_count)
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable:
        if valuation is None or not verifier_valuation(formula, valuation):
            raise RuntimeError("La valuation calculée ne satisfait pas la FNC.")
        for cell, value in decode(encoding, valuation).items():
            print(f"{cell} = {show_value(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
