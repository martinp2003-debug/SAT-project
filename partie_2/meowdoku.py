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
IDENTIFIANT = re.compile(r"[A-Za-z_]\w*\Z")


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


def main() -> int:
    """Lit les arguments et écrit les déclarations CSP de la grille."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grille", type=Path, help="fichier GRID/ZONES à lire")
    parser.add_argument("sortie", type=Path, help="fichier .csp à produire")
    args = parser.parse_args()

    if args.grille.resolve() == args.sortie.resolve():
        parser.error("l'entrée et la sortie doivent être des fichiers distincts")

    try:
        description = lire_description_grille(args.grille)
        texte = generer_declarations(description)
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
