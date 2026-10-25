"""Prétraitement sûr des formules avant la recherche incrémentale."""

from collections.abc import Sequence

from question2.sat import Clause
from question6.structures import ClauseInterne, ProblemeCNF


def _cle_litteral(litteral: int) -> tuple[int, bool]:
    """Définit un ordre déterministe, avec le signe positif en premier."""
    return abs(litteral), litteral < 0


def preprocesser(
    formule: Sequence[Clause], nombre_variables: int
) -> ProblemeCNF:
    """Retire tautologies et doublons sans changer la satisfiabilité."""
    if nombre_variables < 0:
        raise ValueError("Le nombre de variables doit être positif ou nul.")

    clauses: list[ClauseInterne] = []
    deja_vues: set[ClauseInterne] = set()
    for clause in formule:
        if any(-litteral in clause for litteral in clause):
            continue
        normalisee = tuple(sorted(clause, key=_cle_litteral))
        if normalisee not in deja_vues:
            clauses.append(normalisee)
            deja_vues.add(normalisee)
    return ProblemeCNF(nombre_variables, tuple(clauses))
