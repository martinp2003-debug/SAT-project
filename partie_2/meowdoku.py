"""Convertit une grille Meowdoku de la partie I en déclarations CSP."""

import argparse
from pathlib import Path
import re
import sys


# Le lecteur de la partie I reste la source unique du contrat GRID/ZONES.
PART_1 = Path(__file__).resolve().parent.parent / "partie_1"
if str(PART_1) not in sys.path:
    sys.path.insert(0, str(PART_1))

from question1.conversion import DescriptionGrille, lire_description_grille  # noqa: E402


MOTS_RESERVES = frozenset({
    "const", "enum", "var", "array", "bool", "constraint",
    "forall", "in", "not", "and", "or",
})
NOMS_GENERES = frozenset({"N", "M", "K", "Zone", "region"})
NOMS_REGLES_POSITIONS = frozenset({
    "row", "col", "z", "z1", "z2", "i", "j", "k", "l",
})
NOMS_REGLES_CASES = frozenset({"cat", "i", "j", "l", "i1", "j1", "i2", "j2"})
IDENTIFIANT = re.compile(r"[A-Za-z_]\w*\Z")


REGLES_POSITIONS = """// Position du chat de chaque région.
array row[Zone] : 1..N;
array col[Zone] : 1..M;

constraint allDifferent(row[*]);
constraint allDifferent(col[*]);

forall z in Zone, i in 1..N, j in 1..M {
    constraint region[i][j] != z -> not (row[z] = i and col[z] = j);
}

forall z1 in Zone, z2 in Zone, i in 1..N, j in 1..M,
       k in (i - 1)..(i + 1), l in (j - 1)..(j + 1) {
    constraint z1 < z2 and k != i and l != j
        -> not (row[z1] = i and col[z1] = j
                and row[z2] = k and col[z2] = l);
}
"""


REGLES_CASES_Q62 = """// Une variable booléenne par case.
array cat[N][M] : bool;

forall i in 1..N { constraint exactlyOne(cat[i][*]); }
forall j in 1..M { constraint exactlyOne(cat[*][j]); }

forall i in 1..(N - 1), j in 1..M, l in (j - 1)..(j + 1) {
    constraint l >= 1 and l <= M and l != j
        -> not (cat[i][j] and cat[i + 1][l]);
}

// Une seule orientation lexicographique par paire de cases d'une même région.
forall i1 in 1..N, j1 in 1..M, i2 in 1..N, j2 in 1..M {
    constraint region[i1][j1] = region[i2][j2]
               and (i1 < i2 or (i1 = i2 and j1 < j2))
        -> not (cat[i1][j1] and cat[i2][j2]);
}
"""


REGLES_CASES = """// Une variable booléenne par case.
array cat[N][M] : bool;

// K est libre : les régions imposent l'existence des chats ; les lignes et
// colonnes imposent seulement leur unicité.
forall i in 1..N { constraint atMostOne(cat[i][*]); }
forall j in 1..M { constraint atMostOne(cat[*][j]); }

forall i in 1..(N - 1), j in 1..M, l in (j - 1)..(j + 1) {
    constraint l >= 1 and l <= M and l != j
        -> not (cat[i][j] and cat[i + 1][l]);
}

// Une seule orientation lexicographique par paire de cases d'une même région.
forall i1 in 1..N, j1 in 1..M, i2 in 1..N, j2 in 1..M {
    constraint region[i1][j1] = region[i2][j2]
               and (i1 < i2 or (i1 = i2 and j1 < j2))
        -> not (cat[i1][j1] and cat[i2][j2]);
}
"""


def _valider_noms_zones(zones: tuple[str, ...]) -> None:
    """Vérifie que les noms de zones peuvent être conservés dans le CSP."""
    for zone in zones:
        if IDENTIFIANT.fullmatch(zone) is None:
            raise ValueError(
                f"nom de zone incompatible avec le langage CSP : {zone!r}"
            )
        if zone in MOTS_RESERVES:
            raise ValueError(f"le nom de zone {zone!r} est un mot réservé CSP")
        if zone in NOMS_GENERES:
            raise ValueError(
                f"le nom de zone {zone!r} entre en conflit avec une déclaration générée"
            )


def generer_declarations(description: DescriptionGrille) -> str:
    """Produit les constantes, l'énumération et la matrice d'une grille."""
    _valider_noms_zones(description.zones)
    lignes = [
        f"const N = {description.n};",
        f"const M = {description.m};",
        f"const K = {len(description.zones)};",
        f"enum Zone = {{ {', '.join(description.zones)} }};",
        "const region[N][M] = [",
    ]
    for numero, ligne in enumerate(description.grille):
        virgule = "," if numero < description.n - 1 else ""
        lignes.append(f"    [{', '.join(ligne)}]{virgule}")
    lignes.append("];\n")
    return "\n".join(lignes)


def _verifier_hypothese_carree(description: DescriptionGrille) -> None:
    k = len(description.zones)
    if description.n != description.m or description.n != k:
        raise ValueError(
            "les modèles de la question 6.2 exigent N = M = K "
            f"(reçu N={description.n}, M={description.m}, K={k})"
        )


def _generer_regions_non_vides(
    description: DescriptionGrille, *, redondante: bool = False
) -> str:
    """Produit une grande disjonction des cases de chaque région."""
    cases_par_zone = {zone: [] for zone in description.zones}
    for i, ligne in enumerate(description.grille, start=1):
        for j, zone in enumerate(ligne, start=1):
            cases_par_zone[zone].append(f"cat[{i}][{j}]")

    nature = "Contrainte redondante" if redondante else "Contrainte de région"
    lignes = [f"// {nature} : au moins un chat dans chaque région."]
    for zone in description.zones:
        lignes.append(f"constraint atLeastOne({', '.join(cases_par_zone[zone])});")
    return "\n".join(lignes) + "\n"


def _verifier_conflits_regles(
    description: DescriptionGrille, generated_names: frozenset[str]
) -> None:
    conflicts = generated_names.intersection(description.zones)
    if conflicts:
        name = min(conflicts)
        raise ValueError(
            f"le nom de zone {name!r} entre en conflit avec les règles générées"
        )


def generer_modele_q62(
    description: DescriptionGrille,
    representation: str,
    redundant_regions: bool = False,
) -> str:
    """Reproduit les modèles carrés utilisés dans les questions 6.2 à 6.4."""
    try:
        rules, generated_names = {
            "positions": (REGLES_POSITIONS, NOMS_REGLES_POSITIONS),
            "cells": (REGLES_CASES_Q62, NOMS_REGLES_CASES),
        }[representation]
    except KeyError:
        raise ValueError(f"modèle Meowdoku inconnu : {representation}") from None
    if redundant_regions and representation != "cells":
        raise ValueError(
            "la contrainte redondante par région exige le modèle cells"
        )
    _verifier_hypothese_carree(description)
    _verifier_conflits_regles(description, generated_names)
    source = generer_declarations(description) + "\n" + rules
    if redundant_regions:
        source += "\n" + _generer_regions_non_vides(
            description, redondante=True
        )
    return source


def generer_modele(description: DescriptionGrille, representation: str) -> str:
    """Produit le modèle demandé, avec ``cells`` généralisé à N, M et K libres."""
    if representation == "positions":
        return generer_modele_q62(description, representation)
    if representation != "cells":
        raise ValueError(f"modèle Meowdoku inconnu : {representation}")

    _verifier_conflits_regles(description, NOMS_REGLES_CASES)
    return (
        generer_declarations(description)
        + "\n"
        + REGLES_CASES
        + "\n"
        + _generer_regions_non_vides(description)
    )


def decoder_solution(description: DescriptionGrille, representation: str, values: dict):
    """Normalise le décodage CSP en ``région -> coordonnées 0-based``."""
    if representation == "positions":
        rows = {
            str(cell.indices[0]): value
            for cell, value in values.items()
            if cell.name == "row"
        }
        columns = {
            str(cell.indices[0]): value
            for cell, value in values.items()
            if cell.name == "col"
        }
        if set(rows) != set(description.zones) or set(columns) != set(description.zones):
            raise ValueError("le décodage ne contient pas une position par région")
        return {zone: (rows[zone] - 1, columns[zone] - 1) for zone in description.zones}

    if representation == "cells":
        solution = {}
        for cell, value in values.items():
            if cell.name != "cat" or not value:
                continue
            i, j = cell.indices
            if not (1 <= i <= description.n and 1 <= j <= description.m):
                raise ValueError(f"case de chat hors grille : ({i}, {j})")
            zone = description.grille[i - 1][j - 1]
            if zone in solution:
                raise ValueError(f"plusieurs chats trouvés dans la région {zone}")
            solution[zone] = (i - 1, j - 1)
        if set(solution) != set(description.zones):
            raise ValueError("le décodage ne contient pas un chat par région")
        return solution

    raise ValueError(f"modèle Meowdoku inconnu : {representation}")


def main() -> int:
    """Lit les arguments et écrit les déclarations CSP de la grille."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grille", type=Path, help="fichier GRID/ZONES à lire")
    parser.add_argument("sortie", type=Path, help="fichier .csp à produire")
    parser.add_argument(
        "--model", choices=("positions", "cells"),
        help="ajouter les règles du modèle Meowdoku demandé",
    )
    args = parser.parse_args()

    if args.grille.resolve() == args.sortie.resolve():
        parser.error("l'entrée et la sortie doivent être des fichiers distincts")
    try:
        description = lire_description_grille(args.grille)
        texte = (
            generer_modele(description, args.model)
            if args.model is not None
            else generer_declarations(description)
        )
        args.sortie.parent.mkdir(parents=True, exist_ok=True)
        args.sortie.write_text(texte, encoding="utf-8")
    except (OSError, ValueError) as erreur:
        parser.error(str(erreur))

    print(
        f"{args.sortie} : grille {description.n} × {description.m}, "
        f"{len(description.zones)} régions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
