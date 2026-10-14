"""Résout une grille Meowdoku et écrit la solution au format de la figure 2."""

import argparse
from collections.abc import Mapping
from itertools import combinations
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import TypeAlias, cast


# Permet aussi l'exécution directe : python3 question3/solution.py ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question1.conversion import (  # noqa: E402
    Grille,
    construire_clauses,
    ecrire_dimacs,
    lire_grille,
)
from question2.sat import Valuation, dpll_valuation, lire_dimacs  # noqa: E402


Position: TypeAlias = tuple[int, int]
Solution: TypeAlias = dict[str, Position]


def regions_dans_ordre(grille: Grille) -> list[str]:
    """Renvoie les régions dans leur ordre de première apparition."""
    return list(dict.fromkeys(region for ligne in grille for region in ligne))


def valuation_vers_solution(grille: Grille, valuation: Mapping[int, bool]) -> Solution:
    """Convertit les variables vraies d'une valuation en positions de chats.

    Args:
        grille: Matrice donnant la région de chaque case.
        valuation: Valeurs des variables DIMACS, éventuellement partielles.

    Returns:
        Le dictionnaire ``région -> (ligne, colonne)`` avec des indices Python.

    Raises:
        ValueError: Si plusieurs chats sont associés à la même région.
    """
    m = len(grille[0])
    solution: Solution = {}
    for identifiant, valeur in valuation.items():
        if not valeur:
            continue
        i, j = divmod(identifiant - 1, m)
        if not (0 <= i < len(grille) and 0 <= j < m):
            raise ValueError(f"Variable hors de la grille : {identifiant}.")
        region = grille[i][j]
        if region in solution:
            raise ValueError(f"Plusieurs chats trouvés dans la région {region}.")
        solution[region] = (i, j)
    return solution


def verifier_solution(grille: Grille, solution: Mapping[str, Position]) -> bool:
    """Vérifie indépendamment toutes les règles du Meowdoku.

    La fonction contrôle les bornes, l'association entre régions et cases,
    l'unicité par ligne, colonne et région, ainsi que l'absence de voisinage.
    """
    n, m = len(grille), len(grille[0])
    regions = {region for ligne in grille for region in ligne}
    if set(solution) != regions:
        return False

    positions = list(solution.values())
    if len(set(positions)) != len(positions):
        return False
    for region, (i, j) in solution.items():
        if not (0 <= i < n and 0 <= j < m):
            return False
        if grille[i][j] != region:
            return False

    if len({i for i, _ in positions}) != len(positions):
        return False
    if len({j for _, j in positions}) != len(positions):
        return False
    return all(
        max(abs(i - ni), abs(j - nj)) > 1
        for (i, j), (ni, nj) in combinations(positions, 2)
    )


def resoudre_grille(chemin: str | Path, seed: int | None = None) -> tuple[Grille, Solution]:
    """Convertit une grille en DIMACS, la résout et valide la solution obtenue.

    Args:
        chemin: Fichier de grille au format GRID/ZONES.
        seed: Graine facultative transmise aux choix aléatoires de DPLL.

    Returns:
        La grille et le dictionnaire des positions de chats.

    Raises:
        ValueError: Si la grille est invalide ou insatisfiable.
        RuntimeError: Si le solveur renvoie une solution qui enfreint une règle.
    """
    grille = lire_grille(chemin)
    clauses = construire_clauses(grille)
    nombre_variables = len(grille) * len(grille[0])

    # Le passage par un fichier DIMACS applique explicitement la chaîne demandée
    # dans l'énoncé : grille -> conversion DIMACS -> solveur SAT.
    with TemporaryDirectory() as dossier:
        fichier_dimacs = Path(dossier) / "grille.cnf"
        ecrire_dimacs(fichier_dimacs, nombre_variables, clauses)
        _, formule = lire_dimacs(fichier_dimacs)

    satisfiable, valuation = dpll_valuation(formule, seed)
    if not satisfiable or valuation is None:
        raise ValueError("Cette grille Meowdoku n'a pas de solution.")
    solution = valuation_vers_solution(grille, cast(Valuation, valuation))
    if not verifier_solution(grille, solution):
        raise RuntimeError("La solution calculée ne respecte pas les règles du jeu.")
    return grille, solution


def formater_solution(grille: Grille, solution: Mapping[str, Position]) -> str:
    """Produit les coordonnées 1-based puis la grille marquée par des ``*``."""
    lignes = [
        f"{region} {solution[region][0] + 1} {solution[region][1] + 1}"
        for region in regions_dans_ordre(grille)
    ]
    lignes.append("")
    positions = set(solution.values())
    lignes.extend(
        " ".join("*" if (i, j) in positions else "." for j in range(len(ligne)))
        for i, ligne in enumerate(grille)
    )
    return "\n".join(lignes) + "\n"


def ecrire_solution(
    entree: str | Path,
    sortie: str | Path,
    grille: Grille,
    solution: Mapping[str, Position],
) -> None:
    """Recopie le fichier d'entrée puis ajoute les deux formats de solution."""
    entree, sortie = Path(entree), Path(sortie)
    contenu = entree.read_text(encoding="utf-8")
    if not contenu.endswith("\n"):
        contenu += "\n"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(contenu + "\n" + formater_solution(grille, solution), encoding="utf-8")


def main() -> None:
    """Résout la grille fournie et écrit le fichier de solution demandé."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grille", type=Path, help="Fichier GRID/ZONES à résoudre")
    parser.add_argument("sortie", type=Path, help="Fichier de solution à produire")
    parser.add_argument("--seed", type=int, help="Graine des choix aléatoires")
    args = parser.parse_args()
    if args.grille.resolve() == args.sortie.resolve():
        parser.error("L'entrée et la sortie doivent être des fichiers distincts.")
    try:
        grille, solution = resoudre_grille(args.grille, args.seed)
        ecrire_solution(args.grille, args.sortie, grille, solution)
    except (OSError, ValueError, RuntimeError) as erreur:
        parser.error(str(erreur))
    print(f"{args.sortie} : solution valide avec {len(solution)} chats.")


if __name__ == "__main__":
    main()
