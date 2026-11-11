"""Question 2 : lecture DIMACS et deux versions de DPLL, sans dépendance."""

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
import random
import sys
from time import process_time
from typing import TypeAlias, cast


Litteral: TypeAlias = int
Clause: TypeAlias = frozenset[Litteral]
Formule: TypeAlias = list[Clause]
Valuation: TypeAlias = dict[int, bool]
ResultatDPLL: TypeAlias = tuple[bool, Valuation | None]


def lire_dimacs(chemin: str | Path) -> tuple[int, Formule]:
    """Lit et valide une formule CNF au format DIMACS.

    Args:
        chemin: Chemin du fichier DIMACS à lire.

    Returns:
        Un couple contenant le nombre de variables et la liste des clauses.
        Chaque clause est un ``frozenset`` de littéraux entiers.

    Le marqueur 0 termine une clause, même si elle s'étend sur plusieurs lignes.
    Les doublons de littéraux sont retirés, mais les clauses vides sont conservées.

    Raises:
        OSError: Si le fichier ne peut pas être lu.
        ValueError: Si son contenu ne respecte pas le format DIMACS attendu.
    """
    entete: tuple[int, int] | None = None
    clauses: Formule = []
    clause: list[Litteral] = []
    for numero, ligne in enumerate(
        Path(chemin).read_text(encoding="utf-8").splitlines(), start=1
    ):
        mots = ligne.split()
        if not mots or mots[0].startswith("c"):
            continue
        if mots[0] == "p":
            if entete is not None or len(mots) != 4 or mots[1] != "cnf":
                raise ValueError(f"Ligne {numero} : en-tête p cnf invalide ou répété.")
            entete = cast(tuple[int, int], tuple(map(int, mots[2:])))
            if any(valeur < 0 for valeur in entete):
                raise ValueError("Les nombres de variables et de clauses doivent être positifs ou nuls.")
            continue
        if entete is None:
            raise ValueError("L'en-tête p cnf doit précéder les clauses.")
        for mot in mots:
            litteral = int(mot)
            if litteral == 0:
                clauses.append(frozenset(clause))
                clause = []
            elif abs(litteral) > entete[0]:
                raise ValueError(f"Ligne {numero} : variable hors de l'en-tête.")
            else:
                clause.append(litteral)
    if entete is None:
        raise ValueError("En-tête p cnf manquant.")
    if clause:
        raise ValueError("La dernière clause doit se terminer par 0.")
    if len(clauses) != entete[1]:
        raise ValueError(f"{entete[1]} clauses annoncées, {len(clauses)} lues.")
    return entete[0], clauses


def simplifier(formule: Sequence[Clause], litteral: Litteral) -> Formule:
    """Simplifie une formule en supposant un littéral vrai.

    Args:
        formule: Clauses de la formule CNF à simplifier.
        litteral: Littéral auquel la valeur vraie est affectée.

    Returns:
        Une nouvelle formule sans les clauses satisfaites ni les occurrences
        du littéral opposé.
    """
    return [clause - {-litteral} for clause in formule if litteral not in clause]


def litteral_force(formule: Sequence[Clause]) -> Litteral | None:
    """Cherche un littéral imposé ou pur.

    Args:
        formule: Clauses de la formule CNF courante.

    Returns:
        Le littéral de la première clause unitaire, puis un littéral pur s'il
        en existe un, ou ``None`` si aucun choix n'est forcé.
    """
    for clause in formule:
        if len(clause) == 1:
            return next(iter(clause))
    litteraux = {litteral for clause in formule for litteral in clause}
    purs = [litteral for litteral in litteraux if -litteral not in litteraux]
    return min(purs, key=abs) if purs else None


def choix_aleatoire(
    formule: Sequence[Clause], aleatoire: random.Random
) -> Litteral:
    """Choisit une variable présente et le signe de son littéral.

    Args:
        formule: Formule CNF non vide dans laquelle effectuer le choix.
        aleatoire: Générateur pseudo-aléatoire utilisé pour le tirage.

    Returns:
        Le littéral choisi, positif ou négatif.
    """
    variables = sorted({abs(litteral) for clause in formule for litteral in clause})
    return aleatoire.choice(variables) * aleatoire.choice((1, -1))


def dpll(formule: Sequence[Clause], seed: int | None = None) -> bool:
    """Détermine si une formule CNF est satisfiable avec l'algorithme 1.

    Args:
        formule: Clauses de la formule CNF à résoudre.
        seed: Graine facultative des choix pseudo-aléatoires.

    Returns:
        ``True`` si la formule est satisfiable, sinon ``False``.
    """
    aleatoire = random.Random(seed)

    def chercher(formule: Sequence[Clause]) -> bool:
        # Les appels récursifs unitaires/purs sont remplacés par une boucle.
        while True:
            if any(not clause for clause in formule):
                return False
            if not formule:
                return True
            litteral = litteral_force(formule)
            if litteral is None:
                break
            formule = simplifier(formule, litteral)

        litteral = choix_aleatoire(formule, aleatoire)
        if chercher(simplifier(formule, litteral)):
            return True
        return chercher(simplifier(formule, -litteral))

    return chercher(formule)


def dpll_valuation(
    formule: Sequence[Clause], seed: int | None = None
) -> ResultatDPLL:
    """Résout une formule CNF et construit une valuation avec l'algorithme 2.

    Args:
        formule: Clauses de la formule CNF à résoudre.
        seed: Graine facultative des choix pseudo-aléatoires.

    Returns:
        ``(True, valuation)`` si la formule est satisfiable, sinon
        ``(False, None)``.

    La valuation est un dictionnaire {identifiant: bool}, éventuellement partiel.
    Toute clause initiale contient déjà un littéral vrai dans ce dictionnaire.
    """
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

        litteral = choix_aleatoire(formule, aleatoire)
        for choix in (litteral, -litteral):
            satisfiable, suite = chercher(simplifier(formule, choix))
            if satisfiable:
                valuation[abs(choix)] = choix > 0
                valuation.update(cast(Valuation, suite))
                return True, valuation
        return False, None

    return chercher(formule)


def verifier_valuation(
    formule: Sequence[Clause], valuation: Mapping[int, bool]
) -> bool:
    """Vérifie qu'une valuation satisfait directement chaque clause.

    Args:
        formule: Clauses de la formule CNF à vérifier.
        valuation: Association entre identifiants de variables et booléens.

    Returns:
        ``True`` si chaque clause contient un littéral vrai, sinon ``False``.
    """
    return all(
        any(abs(l) in valuation and valuation[abs(l)] == (l > 0) for l in clause)
        for clause in formule
    )


def main() -> None:
    """Lit la commande, résout l'instance DIMACS et affiche le résultat."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path, help="Fichier DIMACS CNF")
    parser.add_argument("--mode", choices=("dpll",), default="dpll")
    parser.add_argument("--version", choices=(1, 2), type=int, default=2)
    parser.add_argument("--seed", type=int, help="Graine des décisions aléatoires")
    parser.add_argument("--output-model", action="store_true")
    parser.add_argument("--stats", action="store_true", help="Temps CPU sur stderr")
    args = parser.parse_args()
    if args.version == 1 and args.output_model:
        parser.error("--output-model nécessite --version 2 (la valeur par défaut).")
    try:
        nombre_variables, formule = lire_dimacs(args.instance)
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))

    debut = process_time()
    if args.version == 1:
        satisfiable = dpll(formule, args.seed)
        valuation = None
    else:
        satisfiable, valuation = dpll_valuation(formule, args.seed)
    duree = process_time() - debut
    if satisfiable and valuation is not None:
        # Les variables non affectées peuvent prendre une valeur arbitraire.
        valuation = {p: valuation.get(p, False) for p in range(1, nombre_variables + 1)}
        if not verifier_valuation(formule, valuation):
            raise RuntimeError("La valuation calculée ne satisfait pas la formule.")
    print("s SATISFIABLE" if satisfiable else "s UNSATISFIABLE")
    if satisfiable and args.output_model:
        valuation_complete = cast(Valuation, valuation)
        modele = [
            p if valuation_complete[p] else -p
            for p in range(1, nombre_variables + 1)
        ]
        print("v", *modele, 0)
    if args.stats:
        print(f"Temps CPU DPLL (hors lecture et vérification) : {duree:.6f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
