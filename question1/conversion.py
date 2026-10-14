"""Convertit une grille Meowdoku en formule CNF au format DIMACS."""

import argparse
from collections.abc import Sequence
from itertools import combinations
from pathlib import Path
from typing import TypeAlias


Grille: TypeAlias = list[list[str]]
Clause: TypeAlias = list[int]
FormuleCNF: TypeAlias = list[Clause]


def lire_grille(chemin: str | Path) -> Grille:
    """Lit et valide un fichier de grille.

    Args:
        chemin: Chemin du fichier texte au format GRID/ZONES.

    Returns:
        La grille des noms de régions, sous forme d'une liste de lignes.

    Raises:
        OSError: Si le fichier ne peut pas être lu.
        ValueError: Si son contenu ne respecte pas le format attendu.
    """
    lignes = []
    for ligne in Path(chemin).read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("c"):
            lignes.append(ligne.split())

    if len(lignes) < 2 or len(lignes[0]) != 3 or lignes[0][0] != "GRID":
        raise ValueError("Le fichier doit commencer par GRID N M.")
    n, m = map(int, lignes[0][1:])
    if n < 1 or m < 1:
        raise ValueError("Les dimensions doivent être strictement positives.")
    if lignes[1][0] != "ZONES" or len(lignes[1]) < 2:
        raise ValueError("La deuxième ligne doit être ZONES suivie des régions.")

    zones = lignes[1][1:]
    if len(set(zones)) != len(zones):
        raise ValueError("Les noms des régions doivent être distincts.")
    grille = lignes[2:]
    if len(grille) != n or any(len(ligne) != m for ligne in grille):
        raise ValueError(f"La grille doit contenir {n} lignes de {m} cases.")
    presentes = {zone for ligne in grille for zone in ligne}
    if presentes != set(zones):
        raise ValueError("Chaque région déclarée doit apparaître, sans région inconnue.")
    return grille


def variable(i: int, j: int, m: int) -> int:
    """Convertit les indices de case ``(i, j)`` en identifiant DIMACS.

    Args:
        i: Indice de ligne, à partir de 0.
        j: Indice de colonne, à partir de 0.
        m: Nombre de colonnes de la grille.

    Returns:
        L'identifiant DIMACS de la variable, à partir de 1.
    """
    return i * m + j + 1


def au_plus_un(variables: Sequence[int]) -> FormuleCNF:
    """Construit les clauses imposant qu'au plus une variable soit vraie.

    Args:
        variables: Identifiants DIMACS positifs des variables concernées.

    Returns:
        Les clauses binaires négatives correspondant à chaque paire.
    """
    return [[-a, -b] for a, b in combinations(variables, 2)]


def construire_clauses(grille: Sequence[Sequence[str]]) -> FormuleCNF:
    """Encode une grille Meowdoku sous forme de clauses CNF.

    Args:
        grille: Matrice rectangulaire dont chaque chaîne est un nom de région.

    Returns:
        La formule CNF, représentée par une liste de clauses d'entiers DIMACS.
    """
    n, m = len(grille), len(grille[0])
    clauses = []

    # Au plus un chat par ligne et par colonne.
    for i in range(n):
        clauses.extend(au_plus_un([variable(i, j, m) for j in range(m)]))
    for j in range(m):
        clauses.extend(au_plus_un([variable(i, j, m) for i in range(n)]))

    # La région est une donnée fixe ; une variable représente seulement un chat.
    regions = {}
    for i in range(n):
        for j in range(m):
            regions.setdefault(grille[i][j], []).append(variable(i, j, m))
    for cases in regions.values():
        clauses.append(list(cases))  # Au moins un chat dans cette région.
        clauses.extend(au_plus_un(cases))

    # Les voisins horizontaux/verticaux sont déjà exclus par lignes/colonnes.
    # Les deux diagonales descendantes couvrent chaque paire diagonale une fois.
    for i in range(n):
        for j in range(m):
            for di, dj in [(1, -1), (1, 1)]:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m:
                    clauses.append([-variable(i, j, m), -variable(ni, nj, m)])
    return clauses


def ecrire_dimacs(
    chemin: str | Path,
    nombre_variables: int,
    clauses: Sequence[Sequence[int]],
) -> None:
    """Écrit une formule CNF dans un fichier au format DIMACS.

    Args:
        chemin: Chemin du fichier de sortie.
        nombre_variables: Nombre total de variables de la formule.
        clauses: Clauses à écrire, chaque entier étant un littéral DIMACS.

    Returns:
        Rien ; le résultat est écrit dans le fichier indiqué.

    Raises:
        OSError: Si le fichier ou son dossier ne peuvent pas être créés.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8") as fichier:
        fichier.write("c Meowdoku : case (i,j), indices depuis 0, variable i*M+j+1\n")
        fichier.write(f"p cnf {nombre_variables} {len(clauses)}\n")
        for clause in clauses:
            fichier.write(" ".join(map(str, clause)) + " 0\n")


def main() -> None:
    """Lit les arguments de la commande et convertit la grille en fichier CNF."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grille", type=Path, help="Fichier GRID/ZONES à lire")
    parser.add_argument("sortie", type=Path, help="Fichier .cnf à produire")
    args = parser.parse_args()
    if args.grille.resolve() == args.sortie.resolve():
        parser.error("L'entrée et la sortie doivent être des fichiers distincts.")
    try:
        grille = lire_grille(args.grille)
        clauses = construire_clauses(grille)
        nombre_variables = len(grille) * len(grille[0])
        ecrire_dimacs(args.sortie, nombre_variables, clauses)
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))
    print(f"{args.sortie} : {nombre_variables} variables, {len(clauses)} clauses.")


if __name__ == "__main__":
    main()
