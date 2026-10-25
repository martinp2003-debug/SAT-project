"""Interface commune des solveurs DPLL et optimisé du projet."""

import argparse
from pathlib import Path
from typing import cast

from question2.sat import (
    Valuation,
    dpll_valuation,
    lire_dimacs,
    verifier_valuation,
)
from question6.solver import dpll_optimized
from question6.structures import StrategieBranchement


def _valuation_complete(nombre_variables: int, valuation: Valuation) -> Valuation:
    """Affecte False aux variables absentes d'un modèle partiel."""
    return {
        variable: valuation.get(variable, False)
        for variable in range(1, nombre_variables + 1)
    }


def _afficher_resultat(
    satisfiable: bool,
    valuation: Valuation | None,
    nombre_variables: int,
    output_model: bool,
) -> None:
    """Écrit exclusivement le résultat au format demandé par le sujet."""
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable and output_model:
        if valuation is None:
            raise RuntimeError("Le solveur SAT n'a pas produit de valuation.")
        modele = [
            variable if valuation[variable] else -variable
            for variable in range(1, nombre_variables + 1)
        ]
        print("v", *modele, 0)


def main() -> None:
    """Lit une instance, sélectionne le solveur et affiche son résultat."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path, help="Fichier DIMACS CNF")
    parser.add_argument(
        "--mode", choices=("dpll", "optimized"), default="optimized"
    )
    parser.add_argument("--output-model", action="store_true")
    parser.add_argument("--seed", type=int, help="Graine du mode dpll")
    parser.add_argument(
        "--strategie",
        choices=("auto", "h1", "h4"),
        default="auto",
        help="Stratégie du mode optimized (option de développement)",
    )
    args = parser.parse_args()

    try:
        nombre_variables, formule = lire_dimacs(args.instance)
        if args.mode == "dpll":
            satisfiable, valuation = dpll_valuation(formule, args.seed)
        else:
            strategie = (
                None
                if args.strategie == "auto"
                else cast(StrategieBranchement, args.strategie)
            )
            satisfiable, valuation = dpll_optimized(
                formule, nombre_variables, strategie
            )
        if satisfiable:
            if valuation is None:
                raise RuntimeError("Le solveur SAT n'a pas produit de valuation.")
            valuation = _valuation_complete(nombre_variables, valuation)
            if not verifier_valuation(formule, valuation):
                raise RuntimeError("La valuation calculée ne satisfait pas la formule.")
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))

    _afficher_resultat(
        satisfiable, valuation, nombre_variables, args.output_model
    )


if __name__ == "__main__":
    main()
