"""Sélection adaptative de la stratégie et du prochain littéral."""

from collections import defaultdict

from question2.sat import Litteral
from question6.propagation import valeur_litteral
from question6.structures import EtatSolveur, ProblemeCNF, StrategieBranchement


def est_type_meowdoku(probleme: ProblemeCNF) -> bool:
    """Reconnaît la structure dominée par les exclusions binaires négatives."""
    non_vides = [clause for clause in probleme.clauses if clause]
    if not non_vides:
        return False
    binaires_negatives = sum(
        len(clause) == 2 and all(litteral < 0 for litteral in clause)
        for clause in non_vides
    )
    clause_positive = any(all(litteral > 0 for litteral in clause) for clause in non_vides)
    return clause_positive and binaires_negatives / len(non_vides) >= 0.70


def choisir_strategie(probleme: ProblemeCNF) -> StrategieBranchement:
    """Choisit H1 pour Meowdoku et H4/MOMS dans le cas général."""
    return "h1" if est_type_meowdoku(probleme) else "h4"


def _clauses_non_satisfaites(etat: EtatSolveur) -> list[list[Litteral]]:
    """Renvoie les littéraux libres de chaque clause non encore satisfaite."""
    restantes: list[list[Litteral]] = []
    for clause in etat.probleme.clauses:
        if any(valeur_litteral(etat, litteral) == 1 for litteral in clause):
            continue
        libres = [
            litteral
            for litteral in clause
            if valeur_litteral(etat, litteral) == -1
        ]
        restantes.append(libres)
    return restantes


def choisir_litteral_h1(etat: EtatSolveur) -> Litteral | None:
    """Choisit la plus petite variable libre et essaie True en premier."""
    variables = {
        abs(litteral)
        for clause in _clauses_non_satisfaites(etat)
        for litteral in clause
    }
    return min(variables) if variables else None


def choisir_litteral_h4(etat: EtatSolveur) -> Litteral | None:
    """Applique MOMS aux clauses non satisfaites les plus courtes."""
    clauses = [clause for clause in _clauses_non_satisfaites(etat) if clause]
    if not clauses:
        return None
    taille_minimale = min(map(len, clauses))
    positives: dict[int, int] = defaultdict(int)
    negatives: dict[int, int] = defaultdict(int)
    for clause in clauses:
        if len(clause) != taille_minimale:
            continue
        for litteral in clause:
            if litteral > 0:
                positives[litteral] += 1
            else:
                negatives[-litteral] += 1
    variables = set(positives) | set(negatives)
    variable = max(variables, key=lambda p: (positives[p] + negatives[p], -p))
    return variable if positives[variable] >= negatives[variable] else -variable


def choisir_litteral(
    etat: EtatSolveur, strategie: StrategieBranchement
) -> Litteral | None:
    """Délègue le choix à la stratégie fixée au début de la recherche."""
    if strategie == "h1":
        return choisir_litteral_h1(etat)
    return choisir_litteral_h4(etat)
