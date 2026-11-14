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
from execution import compile_program, prepare_program, solve_encoding
from expansion import show
from syntax import parse, pretty, syntax_error_message


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
        if args.expand:
            _, expansion = prepare_program(program)
        else:
            _, expansion, encoding = compile_program(program, args.amo)
        for warning in expansion.warnings:
            print(f"{args.model}: avertissement : {warning}", file=sys.stderr)
        if args.expand:
            for constraint in expansion.constraints:
                print(show(constraint))
            return 0
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

    satisfiable, values = solve_encoding(encoding)
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable:
        for cell, value in values.items():
            print(f"{cell} = {show_value(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
