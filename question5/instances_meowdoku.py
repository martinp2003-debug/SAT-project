"""Génère les instances Meowdoku SAT et UNSAT utilisées par la question 5.

Les grilles SAT proviennent du générateur de la question 1. Une grille UNSAT
est obtenue en détachant une case de la plus grande région pour en faire une
région supplémentaire : il faut alors N + 1 chats sur N lignes contenant chacune
au plus un chat, ce qui est impossible (principe des tiroirs).
"""

import argparse
from pathlib import Path
import random
import sys


# Permet aussi l'exécution directe : python3 question5/instances_meowdoku.py ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question1.conversion import construire_clauses, ecrire_dimacs  # noqa: E402
from question1.generation import Grille, ecrire_grille, generer_grille  # noqa: E402


TAILLES_SAT = (6, 8, 10, 12, 14)
TAILLES_UNSAT = (4, 5, 6, 7, 8, 9, 10)
GRAINES = (1, 2)


def rendre_insatisfiable(grille: Grille, seed: int | None = None) -> Grille:
    """Ajoute une région en coupant la plus grande région en deux.

    La moitié détachée est parcourue en largeur depuis une case aléatoire :
    elle reste connexe. Une région d'une seule case donnerait une clause
    unitaire et une contradiction trouvée sans aucune décision ; on demande
    donc au moins quatre cases pour obtenir deux moitiés d'au moins deux cases.
    """
    aleatoire = random.Random(seed)
    cases: dict[str, list[tuple[int, int]]] = {}
    for i, ligne in enumerate(grille):
        for j, region in enumerate(ligne):
            cases.setdefault(region, []).append((i, j))
    plus_grande = max(cases, key=lambda r: (len(cases[r]), r))
    region = set(cases[plus_grande])
    if len(region) < 4:
        raise ValueError("Aucune région ne contient au moins quatre cases.")

    depart = aleatoire.choice(sorted(region))
    moitie, file = [depart], [depart]
    while file and len(moitie) < len(region) // 2:
        i, j = file.pop(0)
        for voisine in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if voisine in region and voisine not in moitie:
                moitie.append(voisine)
                file.append(voisine)
                if len(moitie) == len(region) // 2:
                    break

    nouvelle = "X"
    while nouvelle in cases:
        nouvelle += "X"
    resultat = [list(ligne) for ligne in grille]
    for i, j in moitie:
        resultat[i][j] = nouvelle
    return resultat


def generer_instances(dossier_grilles: Path, dossier_cnf: Path) -> list[Path]:
    """Écrit les grilles et leurs CNF ; renvoie les chemins des CNF créés."""
    chemins = []
    demandes = [("sat", t, g) for t in TAILLES_SAT for g in GRAINES]
    demandes += [("unsat", t, g) for t in TAILLES_UNSAT for g in GRAINES]
    for statut, taille, graine in demandes:
        grille, _ = generer_grille(taille, seed=graine)
        if statut == "unsat":
            grille = rendre_insatisfiable(grille, seed=graine)
        nom = f"meow_{statut}_{taille:02d}_s{graine}"
        ecrire_grille(dossier_grilles / f"{nom}.txt", grille)
        clauses = construire_clauses(grille)
        chemin = dossier_cnf / f"{nom}.cnf"
        ecrire_dimacs(chemin, len(grille) * len(grille[0]), clauses)
        chemins.append(chemin)
    return chemins


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grilles", type=Path, default=Path("grilles/q5"))
    parser.add_argument("--cnf", type=Path, default=Path("instances/q5"))
    args = parser.parse_args()
    for chemin in generer_instances(args.grilles, args.cnf):
        print(chemin)


if __name__ == "__main__":
    main()
