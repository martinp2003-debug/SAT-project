"""Compare le modèle Meowdoku généralisé à une recherche exhaustive."""

import argparse
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import sys


DOSSIER_Q65 = Path(__file__).resolve().parent
PARTIE_2 = DOSSIER_Q65.parent
RACINE = PARTIE_2.parent
PARTIE_1 = RACINE / "partie_1"
for dossier in (PARTIE_2, PARTIE_1):
    if str(dossier) not in sys.path:
        sys.path.insert(0, str(dossier))

from diagnostics import CompilationError  # noqa: E402
from execution import compile_program, solve_encoding  # noqa: E402
from meowdoku import (  # noqa: E402
    decoder_solution,
    generer_modele,
    lire_description_grille,
)
from question1.conversion import DescriptionGrille  # noqa: E402
from question3.solution import Solution, verifier_solution  # noqa: E402
from syntax import parse  # noqa: E402


@dataclass(frozen=True)
class Comparaison:
    """Résultat des deux recherches indépendantes sur une grille."""

    sat_compilateur: bool
    sat_exhaustif: bool
    solution_compilateur: Solution | None
    solution_exhaustive: Solution | None


def rechercher_solution_exhaustive(
    description: DescriptionGrille,
) -> Solution | None:
    """Énumère une case par région sans utiliser le compilateur ni DPLL."""
    cases_par_zone: dict[str, list[tuple[int, int]]] = {
        zone: [] for zone in description.zones
    }
    for i, ligne in enumerate(description.grille):
        for j, zone in enumerate(ligne):
            cases_par_zone[zone].append((i, j))

    grille = [list(ligne) for ligne in description.grille]
    domaines = [cases_par_zone[zone] for zone in description.zones]
    for positions in product(*domaines):
        solution = dict(zip(description.zones, positions, strict=True))
        if verifier_solution(grille, solution):
            return solution
    return None


def comparer_avec_exhaustif(description: DescriptionGrille) -> Comparaison:
    """Résout par SAT et exhaustivement, puis exige des statuts identiques."""
    source = generer_modele(description, "cells")
    _, _, encoding = compile_program(parse(source))
    sat_compilateur, values = solve_encoding(encoding)

    solution_compilateur = None
    grille = [list(ligne) for ligne in description.grille]
    if sat_compilateur:
        if values is None:
            raise RuntimeError("le solveur SAT n'a pas renvoyé de valuation")
        solution_compilateur = decoder_solution(description, "cells", values)
        if not verifier_solution(grille, solution_compilateur):
            raise RuntimeError("le modèle SAT a produit une solution Meowdoku invalide")

    solution_exhaustive = rechercher_solution_exhaustive(description)
    sat_exhaustif = solution_exhaustive is not None
    if sat_compilateur != sat_exhaustif:
        raise RuntimeError(
            "désaccord de statut : "
            f"compilateur={'SAT' if sat_compilateur else 'UNSAT'}, "
            f"exhaustif={'SAT' if sat_exhaustif else 'UNSAT'}"
        )
    return Comparaison(
        sat_compilateur,
        sat_exhaustif,
        solution_compilateur,
        solution_exhaustive,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "grilles",
        nargs="*",
        type=Path,
        help="petites grilles à comparer (par défaut : question6.5/grilles)",
    )
    args = parser.parse_args()
    grilles = args.grilles or sorted((DOSSIER_Q65 / "grilles").glob("*.txt"))
    if not grilles:
        parser.error("aucune grille à comparer")

    print("grille\tN\tM\tK\tcompilateur\texhaustif")
    try:
        for chemin in grilles:
            description = lire_description_grille(chemin)
            resultat = comparer_avec_exhaustif(description)
            statut_compilateur = "SAT" if resultat.sat_compilateur else "UNSAT"
            statut_exhaustif = "SAT" if resultat.sat_exhaustif else "UNSAT"
            print(
                f"{chemin.name}\t{description.n}\t{description.m}\t"
                f"{len(description.zones)}\t{statut_compilateur}\t{statut_exhaustif}"
            )
    except (OSError, ValueError, RuntimeError, CompilationError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
