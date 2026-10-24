"""DPLL_H instrumenté pour comparer les heuristiques (question 5).

Les compteurs suivent les lignes de l'algorithme 3 du sujet :
décisions (ligne 17), retours arrière (ligne 21), propagations unitaires
(ligne 5) et règles du littéral pur (ligne 11).
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
import random
import sys
from time import process_time_ns
from typing import cast


# Permet aussi l'exécution directe : python3 question5/instrumentation.py ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question2.sat import (  # noqa: E402
    Clause,
    Litteral,
    ResultatDPLL,
    Valuation,
    simplifier,
)
from question4.heuristiques import (  # noqa: E402
    NOMS_HEURISTIQUES,
    NomHeuristique,
    choisir_litteral,
)


Choix = Callable[[Sequence[Clause]], Litteral]

# Les variantes statiques classent les littéraux une fois pour toutes sur la
# formule initiale, puis prennent le premier dont la variable est encore libre.
NOMS_STATIQUES: tuple[str, ...] = ("h3s", "h7s")
TOUTES_HEURISTIQUES: tuple[str, ...] = NOMS_HEURISTIQUES + NOMS_STATIQUES


class DelaiDepasse(Exception):
    """Levée lorsque le temps CPU accordé à une résolution est épuisé."""


@dataclass
class Statistiques:
    """Mesures collectées pendant une exécution de DPLL_H."""

    decisions: int = 0
    retours_arriere: int = 0
    propagations_unitaires: int = 0
    litteraux_purs: int = 0
    noeuds: int = 0
    profondeur_max: int = 0
    temps_cpu_ms: float = 0.0
    temps_heuristique_ms: float = 0.0
    interrompu: bool = False

    @property
    def ratio_heuristique(self) -> float:
        """Part du temps CPU consacrée au choix de branchement."""
        if self.temps_cpu_ms == 0:
            return 0.0
        return self.temps_heuristique_ms / self.temps_cpu_ms


@dataclass
class ResultatInstrumente:
    """Statut (``None`` si interrompu), valuation éventuelle et mesures."""

    satisfiable: bool | None
    valuation: Valuation | None
    statistiques: Statistiques = field(default_factory=Statistiques)


def litteral_force_type(formule: Sequence[Clause]) -> tuple[Litteral, str] | None:
    """Comme ``question2.sat.litteral_force``, en indiquant la règle appliquée.

    Returns:
        ``(littéral, "unitaire")``, ``(littéral, "pur")`` ou ``None``.
    """
    for clause in formule:
        if len(clause) == 1:
            return next(iter(clause)), "unitaire"
    litteraux = {litteral for clause in formule for litteral in clause}
    purs = [litteral for litteral in litteraux if -litteral not in litteraux]
    return (min(purs, key=abs), "pur") if purs else None


def ordre_statique(formule: Sequence[Clause], heuristique: str) -> list[Litteral]:
    """Classe les littéraux de la formule initiale selon H3 ou H7.

    Les égalités sont départagées comme dans la question 4 : plus petite
    variable, puis polarité positive.
    """
    scores: dict[Litteral, float] = defaultdict(float)
    for clause in formule:
        poids = 1.0 if heuristique == "h3s" else 2.0 ** -len(clause)
        for litteral in clause:
            scores[litteral] += poids
    return sorted(scores, key=lambda l: (-scores[l], abs(l), l < 0))


def choix_statique(ordre: Sequence[Litteral]) -> Choix:
    """Renvoie le premier littéral de l'ordre dont la variable est libre."""

    def choisir(formule: Sequence[Clause]) -> Litteral:
        presentes = {abs(litteral) for clause in formule for litteral in clause}
        for litteral in ordre:
            if abs(litteral) in presentes:
                return litteral
        raise ValueError("Impossible de choisir dans une formule sans variable.")

    return choisir


def construire_choix(
    formule: Sequence[Clause], heuristique: str, seed: int | None
) -> Choix:
    """Prépare la fonction de branchement correspondant au nom donné."""
    if heuristique in NOMS_STATIQUES:
        return choix_statique(ordre_statique(formule, heuristique))
    if heuristique in NOMS_HEURISTIQUES:
        aleatoire = random.Random(seed)
        nom = cast(NomHeuristique, heuristique)
        return lambda f: choisir_litteral(f, nom, aleatoire)
    raise ValueError(f"Heuristique inconnue : {heuristique}.")


def dpll_h_instrumente(
    formule: Sequence[Clause],
    heuristique: str = "h1",
    seed: int | None = None,
    limite_s: float | None = None,
) -> ResultatInstrumente:
    """Résout une formule avec DPLL_H en comptant les opérations effectuées.

    L'exploration est identique à ``question4.heuristiques.dpll_h``. Si
    ``limite_s`` est fourni et que le temps CPU le dépasse, la recherche est
    abandonnée : le statut vaut alors ``None`` et ``interrompu`` est vrai.
    Le prétraitement des variantes statiques est compté dans le temps de
    l'heuristique.
    """
    stats = Statistiques()
    debut = process_time_ns()
    echeance = None if limite_s is None else debut + int(limite_s * 1e9)
    choisir = construire_choix(formule, heuristique, seed)
    stats.temps_heuristique_ms = (process_time_ns() - debut) / 1e6

    def chercher(formule: Sequence[Clause], profondeur: int) -> ResultatDPLL:
        stats.noeuds += 1
        stats.profondeur_max = max(stats.profondeur_max, profondeur)
        if echeance is not None and process_time_ns() > echeance:
            raise DelaiDepasse
        valuation: Valuation = {}
        while True:
            if any(not clause for clause in formule):
                return False, None
            if not formule:
                return True, valuation
            force = litteral_force_type(formule)
            if force is None:
                break
            litteral, regle = force
            if regle == "unitaire":
                stats.propagations_unitaires += 1
            else:
                stats.litteraux_purs += 1
            valuation[abs(litteral)] = litteral > 0
            formule = simplifier(formule, litteral)

        stats.decisions += 1
        debut_choix = process_time_ns()
        litteral = choisir(formule)
        stats.temps_heuristique_ms += (process_time_ns() - debut_choix) / 1e6
        for numero, choix in enumerate((litteral, -litteral)):
            if numero == 1:
                stats.retours_arriere += 1
            satisfiable, suite = chercher(simplifier(formule, choix), profondeur + 1)
            if satisfiable:
                valuation[abs(choix)] = choix > 0
                valuation.update(cast(Valuation, suite))
                return True, valuation
        return False, None

    try:
        satisfiable, valuation = chercher(formule, 0)
        resultat = ResultatInstrumente(satisfiable, valuation, stats)
    except DelaiDepasse:
        stats.interrompu = True
        resultat = ResultatInstrumente(None, None, stats)
    stats.temps_cpu_ms = (process_time_ns() - debut) / 1e6
    return resultat
