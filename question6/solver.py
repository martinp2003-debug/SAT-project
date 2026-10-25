"""DPLL incrémental avec littéraux surveillés et heuristique adaptative."""

from collections.abc import Sequence
import sys

from question2.sat import Clause, ResultatDPLL, Valuation
from question6.branching import choisir_litteral, choisir_strategie
from question6.preprocessing import preprocesser
from question6.propagation import (
    affecter,
    annuler_niveau,
    initialiser_etat,
    ouvrir_niveau,
    propager,
)
from question6.structures import EtatSolveur, StrategieBranchement


def _construire_valuation(etat: EtatSolveur) -> Valuation:
    """Construit une valuation complète, False pour les variables libres."""
    return {
        variable: etat.affectations[variable] == 1
        for variable in range(1, etat.probleme.nombre_variables + 1)
    }


def _chercher(etat: EtatSolveur, strategie: StrategieBranchement) -> bool:
    """Explore récursivement les décisions, en annulant seulement le trail."""
    litteral = choisir_litteral(etat, strategie)
    if litteral is None:
        return True

    for choix in (litteral, -litteral):
        ouvrir_niveau(etat)
        if affecter(etat, choix) and propager(etat) and _chercher(etat, strategie):
            return True
        annuler_niveau(etat)
    return False


def dpll_optimized(
    formule: Sequence[Clause],
    nombre_variables: int,
    strategie: StrategieBranchement | None = None,
) -> ResultatDPLL:
    """Résout une CNF sans la recopier, avec une stratégie imposée ou adaptée."""
    sys.setrecursionlimit(
        max(sys.getrecursionlimit(), 2 * nombre_variables + 100)
    )
    probleme = preprocesser(formule, nombre_variables)
    etat = initialiser_etat(probleme)
    if not propager(etat):
        return False, None
    strategie_effective = strategie or choisir_strategie(probleme)
    if not _chercher(etat, strategie_effective):
        return False, None
    return True, _construire_valuation(etat)
