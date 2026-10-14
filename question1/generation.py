"""Génère une grille Meowdoku résoluble dans le cas N = M = K."""

import argparse
import random
from collections.abc import Sequence
from pathlib import Path
from typing import TypeAlias, cast


Position: TypeAlias = tuple[int, int]
Grille: TypeAlias = list[list[str]]
ResultatGeneration: TypeAlias = tuple[Grille, list[Position]]


def generer_grille(taille: int, seed: int | None = None) -> ResultatGeneration:
    """Génère une grille carrée et une solution associée.

    Args:
        taille: Valeur commune de N, M et K.
        seed: Graine aléatoire facultative permettant de reproduire la grille.

    Returns:
        Un couple contenant la grille des régions et les positions ``(i, j)``
        des chats d'une solution, avec des indices commençant à 0.

    Raises:
        ValueError: Si la taille est inférieure à 1 ou vaut 2 ou 3.
    """
    if taille < 1:
        raise ValueError("La taille doit être strictement positive.")
    if taille in (2, 3):
        raise ValueError("Aucune solution n'existe pour N = M = K = 2 ou 3.")
    aleatoire = random.Random(seed)

    # Essayer les départs dans un ordre aléatoire, sans répétition.
    # Les indices de colonnes vont de 0 à taille - 1.
    departs = list(range(taille))
    aleatoire.shuffle(departs)
    for depart in departs:
        # Avancer de 2, parcourir l'autre parité depuis son plus petit indice,
        # puis reprendre les colonnes de la parité initiale restées avant depart.
        autre_parite = 1 - depart % 2
        colonnes = (
            list(range(depart, taille, 2))
            + list(range(autre_parite, taille, 2))
            + list(range(depart % 2, depart, 2))
        )
        # Les raccords entre ces groupes peuvent créer un contact diagonal.
        # Si c'est le cas, essayer le départ suivant. Le départ 1 fonctionne
        # toujours pour taille >= 4 ; pour taille 1, le seul départ est 0.
        if all(abs(a - b) >= 2 for a, b in zip(colonnes, colonnes[1:])):
            break
    chats = list(enumerate(colonnes))

    grille: list[list[str | None]] = [
        [None for _ in range(taille)] for _ in range(taille)
    ]
    for numero, (i, j) in enumerate(chats, start=1):
        grille[i][j] = f"R{numero}"

    # Chaque région grandit depuis son chat, par voisinage horizontal/vertical.
    # Les cases occupées ne sont jamais réattribuées : chaque région garde
    # exactement son chat et reste connexe.
    frontiere: list[tuple[int, int, str]] = []

    def ajouter_voisines(i: int, j: int) -> None:
        """Ajoute à la frontière les voisines libres de la case ``(i, j)``."""
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < taille and 0 <= nj < taille and grille[ni][nj] is None:
                frontiere.append((ni, nj, cast(str, grille[i][j])))

    for i, j in chats:
        ajouter_voisines(i, j)
    while frontiere:
        index = aleatoire.randrange(len(frontiere))
        frontiere[index], frontiere[-1] = frontiere[-1], frontiere[index]
        i, j, region = frontiere.pop()
        if grille[i][j] is None:
            grille[i][j] = region
            ajouter_voisines(i, j)

    # Toutes les cases ont été atteintes par la croissance des régions.
    return cast(Grille, grille), chats


def ecrire_grille(chemin: str | Path, grille: Sequence[Sequence[str]]) -> None:
    """Enregistre une grille au format texte GRID/ZONES.

    Args:
        chemin: Chemin du fichier de sortie.
        grille: Matrice rectangulaire contenant le nom de région de chaque case.

    Returns:
        Rien ; la grille est écrite dans le fichier indiqué.

    Raises:
        OSError: Si le fichier ou son dossier ne peuvent pas être créés.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    n, m = len(grille), len(grille[0])
    regions = list(dict.fromkeys(zone for ligne in grille for zone in ligne))
    with chemin.open("w", encoding="utf-8") as fichier:
        fichier.write("c Grille Meowdoku générée avec au moins une solution\n")
        fichier.write(f"GRID {n} {m}\n")
        fichier.write("ZONES " + " ".join(regions) + "\n")
        for ligne in grille:
            fichier.write(" ".join(ligne) + "\n")


def main() -> None:
    """Lit les arguments de la commande et génère le fichier de grille."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("taille", type=int, help="Valeur commune de N, M et K")
    parser.add_argument("sortie", type=Path, help="Fichier grille à produire")
    parser.add_argument("--seed", type=int, help="Graine pour reproduire une grille")
    args = parser.parse_args()
    try:
        grille, _ = generer_grille(args.taille, args.seed)
        ecrire_grille(args.sortie, grille)
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))
    print(f"{args.sortie} : grille {args.taille} × {args.taille}, {args.taille} régions.")


if __name__ == "__main__":
    main()
