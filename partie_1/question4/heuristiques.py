"""Algorithme DPLL_H et heuristiques de branchement de la question 4."""

import argparse
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
import random
import sys
from typing import Literal, TypeAlias, cast


# Permet aussi l'exécution directe : python3 question4/heuristiques.py ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question2.sat import (  # noqa: E402
    Clause,
    Formule,
    Litteral,
    ResultatDPLL,
    Valuation,
    choix_aleatoire,
    lire_dimacs,
    litteral_force,
    simplifier,
    verifier_valuation,
)


NomHeuristique: TypeAlias = Literal["h0", "h1", "h3", "h4", "h7"]
NOMS_HEURISTIQUES: tuple[NomHeuristique, ...] = ("h0", "h1", "h3", "h4", "h7")


def _meilleur_litteral(scores: dict[Litteral, float]) -> Litteral:
    """Maximise un score, puis préfère la petite variable et le signe positif."""
    if not scores:
        raise ValueError("Impossible de choisir dans une formule sans littéral.")
    return min(scores, key=lambda l: (-scores[l], abs(l), l < 0))


def premiere_variable_libre(formule: Sequence[Clause]) -> Litteral:
    """H1 (PVL) : choisit la première variable libre et la valeur vraie."""
    variables = {abs(litteral) for clause in formule for litteral in clause}
    if not variables:
        raise ValueError("Impossible de choisir dans une formule sans variable.")
    return min(variables)


def litteral_plus_frequent(formule: Sequence[Clause]) -> Litteral:
    """H3 (LP) dynamique : maximise le nombre d'occurrences du littéral."""
    scores: dict[Litteral, float] = defaultdict(float)
    for clause in formule:
        for litteral in clause:
            scores[litteral] += 1
    return _meilleur_litteral(scores)


def variable_frequente_clauses_minimales(formule: Sequence[Clause]) -> Litteral:
    """H4 (VFCM) dynamique : fréquence dans les clauses de taille minimale.

    La polarité choisie est majoritaire parmi ces mêmes clauses. Les égalités
    sont départagées par le plus petit identifiant, puis par le signe positif.
    """
    if not formule:
        raise ValueError("Impossible de choisir dans une formule vide.")
    taille_minimale = min(map(len, formule))
    positives: dict[int, int] = defaultdict(int)
    negatives: dict[int, int] = defaultdict(int)
    for clause in formule:
        if len(clause) != taille_minimale:
            continue
        for litteral in clause:
            if litteral > 0:
                positives[litteral] += 1
            else:
                negatives[-litteral] += 1
    variables = set(positives) | set(negatives)
    if not variables:
        raise ValueError("Aucune variable dans les clauses minimales.")
    variable = max(
        variables,
        key=lambda p: (positives[p] + negatives[p], -p),
    )
    return variable if positives[variable] >= negatives[variable] else -variable


def litteral_jw(formule: Sequence[Clause]) -> Litteral:
    """H7 (LJW) dynamique : maximise la pondération de Jeroslow–Wang."""
    scores: dict[Litteral, float] = defaultdict(float)
    for clause in formule:
        poids = 2.0 ** -len(clause)
        for litteral in clause:
            scores[litteral] += poids
    return _meilleur_litteral(scores)


def choisir_litteral(
    formule: Sequence[Clause],
    heuristique: NomHeuristique,
    aleatoire: random.Random,
) -> Litteral:
    """Applique l'heuristique demandée à la formule courante."""
    if heuristique == "h0":
        return choix_aleatoire(formule, aleatoire)
    if heuristique == "h1":
        return premiere_variable_libre(formule)
    if heuristique == "h3":
        return litteral_plus_frequent(formule)
    if heuristique == "h4":
        return variable_frequente_clauses_minimales(formule)
    if heuristique == "h7":
        return litteral_jw(formule)
    raise ValueError(f"Heuristique inconnue : {heuristique}.")


def dpll_h(
    formule: Sequence[Clause],
    heuristique: NomHeuristique = "h1",
    seed: int | None = None,
) -> ResultatDPLL:
    """Résout une formule avec DPLL_H et renvoie aussi une valuation.

    Les clauses unitaires et littéraux purs conservent la priorité. L'heuristique
    intervient uniquement lorsqu'une décision de branchement est nécessaire.
    """
    if heuristique not in NOMS_HEURISTIQUES:
        raise ValueError(f"Heuristique inconnue : {heuristique}.")
    aleatoire = random.Random(seed)

    def chercher(formule: Sequence[Clause]) -> ResultatDPLL:
        valuation: Valuation = {}
        while True:
            if any(not clause for clause in formule):
                return False, None
            if not formule:
                return True, valuation
            litteral = litteral_force(formule)
            if litteral is None:
                break
            valuation[abs(litteral)] = litteral > 0
            formule = simplifier(formule, litteral)

        litteral = choisir_litteral(formule, heuristique, aleatoire)
        for choix in (litteral, -litteral):
            satisfiable, suite = chercher(simplifier(formule, choix))
            if satisfiable:
                valuation[abs(choix)] = choix > 0
                valuation.update(cast(Valuation, suite))
                return True, valuation
        return False, None

    return chercher(formule)


def main() -> None:
    """Lit une instance DIMACS et la résout avec l'heuristique choisie."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path, help="Fichier DIMACS CNF")
    parser.add_argument(
        "--heuristique",
        choices=NOMS_HEURISTIQUES,
        default="h1",
        help="H0 aléatoire, H1 PVL, H3 LP, H4 VFCM ou H7 LJW",
    )
    parser.add_argument("--seed", type=int, help="Graine utilisée par H0")
    parser.add_argument("--output-model", action="store_true")
    args = parser.parse_args()
    try:
        nombre_variables, formule = lire_dimacs(args.instance)
        satisfiable, valuation = dpll_h(
            formule,
            cast(NomHeuristique, args.heuristique),
            args.seed,
        )
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))

    if satisfiable and valuation is not None:
        valuation = {
            p: valuation.get(p, False) for p in range(1, nombre_variables + 1)
        }
        if not verifier_valuation(formule, valuation):
            raise RuntimeError("La valuation calculée ne satisfait pas la formule.")
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable and args.output_model:
        complete = cast(Valuation, valuation)
        modele = [p if complete[p] else -p for p in range(1, nombre_variables + 1)]
        print("v", *modele, 0)


if __name__ == "__main__":
    main()
