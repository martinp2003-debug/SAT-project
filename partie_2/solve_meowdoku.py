"""Génère, résout et vérifie indépendamment un modèle Meowdoku."""

import argparse
from pathlib import Path
import sys

from diagnostics import CompilationError
from execution import compile_program, solve_encoding
from meowdoku import decoder_solution, generer_modele, lire_description_grille
from syntax import parse


PART_1 = Path(__file__).resolve().parent.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question3.solution import formater_solution, verifier_solution  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grille", type=Path, help="fichier GRID/ZONES à résoudre")
    parser.add_argument("--model", required=True, choices=("positions", "cells"))
    parser.add_argument("--amo", choices=("pairwise", "sinz"), default="pairwise")
    parser.add_argument(
        "--redundant-regions",
        action="store_true",
        help="ajouter au modèle cells au moins un chat par région",
    )
    args = parser.parse_args()
    if args.redundant_regions and args.model != "cells":
        parser.error("--redundant-regions exige --model cells")

    try:
        description = lire_description_grille(args.grille)
        source = generer_modele(
            description,
            args.model,
            redundant_regions=args.redundant_regions,
        )
        _, expanded, encoding = compile_program(parse(source), args.amo)
        for warning in expanded.warnings:
            print(f"{args.grille}: avertissement : {warning}", file=sys.stderr)
        satisfiable, values = solve_encoding(encoding)
        if not satisfiable:
            print("s UNSATISFIABLE")
            return 0

        solution = decoder_solution(description, args.model, values)
        grid = [list(row) for row in description.grille]
        if not verifier_solution(grid, solution):
            raise RuntimeError("la solution calculée ne respecte pas les règles du Meowdoku")
    except (OSError, ValueError, RuntimeError, CompilationError) as error:
        parser.error(str(error))

    print("s SATISFIABLE")
    print(formater_solution(grid, solution), end="")
    print("c solution vérifiée indépendamment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
