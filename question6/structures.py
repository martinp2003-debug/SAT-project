"""Structures typées du solveur incrémental de la question 6."""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from question2.sat import Litteral


# Valeurs internes : -1 = libre, 0 = faux, 1 = vrai.
Valeur: TypeAlias = int
ClauseInterne: TypeAlias = tuple[Litteral, ...]
StrategieBranchement: TypeAlias = Literal["h1", "h4"]


@dataclass(frozen=True, slots=True)
class ProblemeCNF:
    """Formule CNF normalisée et immuable."""

    nombre_variables: int
    clauses: tuple[ClauseInterne, ...]


@dataclass(slots=True)
class EtatSolveur:
    """État mutable annulable sans recopier la formule."""

    probleme: ProblemeCNF
    affectations: list[Valeur]
    trail: list[Litteral] = field(default_factory=list)
    prochain_a_propager: int = 0
    niveaux: list[int] = field(default_factory=list)
    positions_surveillees: list[tuple[int, int]] = field(default_factory=list)
    surveillances: list[list[int]] = field(default_factory=list)
    conflit_initial: bool = False
