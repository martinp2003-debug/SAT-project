"""Compare les deux modeles Meowdoku de la question 6.3.

Le protocole garde le compilateur, l'encodage de ``atMostOne`` et le DPLL
instrumente constants. Une ligne CSV correspond a une repetition du solveur
sur un couple (grille, modele). Les mesures de compilation et de structure de
la FNC sont repetees sur chaque ligne afin que le CSV reste autonome.
"""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import median
import sys
from time import process_time_ns


DOSSIER_Q63 = Path(__file__).resolve().parent
PARTIE_2 = DOSSIER_Q63.parent
RACINE = PARTIE_2.parent
PARTIE_1 = RACINE / "partie_1"
for dossier in (PARTIE_2, PARTIE_1):
    if str(dossier) not in sys.path:
        sys.path.insert(0, str(dossier))

from diagnostics import CompilationError
from encoding import decode
from execution import compile_program
from meowdoku import decoder_solution, generer_modele_q62, lire_description_grille
from syntax import parse

from question2.sat import verifier_valuation  # noqa: E402
from question3.solution import verifier_solution  # noqa: E402
from question5.instrumentation import (  # noqa: E402
    TOUTES_HEURISTIQUES,
    dpll_h_instrumente,
)


MODELES = ("positions", "cells")
COLONNES = [
    "instance", "taille", "modele", "amo", "heuristique", "repetition",
    "statut", "compilation_cpu_ms", "contraintes_developpees", "avertissements",
    "variables", "variables_nommees", "variables_auxiliaires", "clauses",
    "clauses_unitaires", "clauses_binaires", "clauses_ternaires",
    "clauses_longues", "occurrences_litteraux", "decisions", "retours_arriere",
    "propagations_unitaires", "litteraux_purs", "noeuds", "profondeur_max",
    "resolution_cpu_ms", "heuristique_cpu_ms", "ratio_heuristique",
]


@dataclass(frozen=True)
class CompilationMesuree:
    """Resultat d'une compilation et metriques independantes du solveur."""

    expanded: object
    encoding: object
    cpu_ms: float


def compiler_modele(source: str, amo: str, repetitions: int) -> CompilationMesuree:
    """Compile plusieurs fois le meme source et conserve le temps CPU median."""
    temps = []
    resultat = None
    for _ in range(repetitions):
        debut = process_time_ns()
        resultat = compile_program(parse(source), amo)
        temps.append((process_time_ns() - debut) / 1e6)
    assert resultat is not None
    _, expanded, encoding = resultat
    return CompilationMesuree(expanded, encoding, median(temps))


def profil_clauses(clauses: list[list[int]]) -> dict[str, int]:
    """Compte les clauses par longueur et les occurrences de litteraux."""
    longueurs = [len(clause) for clause in clauses]
    return {
        "clauses_unitaires": longueurs.count(1),
        "clauses_binaires": longueurs.count(2),
        "clauses_ternaires": longueurs.count(3),
        "clauses_longues": sum(longueur >= 4 for longueur in longueurs),
        "occurrences_litteraux": sum(longueurs),
    }


def mesurer_modele(
    grille: Path,
    modele: str,
    amo: str = "pairwise",
    heuristique: str = "h1",
    repetitions: int = 3,
    repetitions_compilation: int = 3,
    limite_s: float = 30.0,
) -> list[dict[str, object]]:
    """Compile, resout et verifie un modele d'une grille SAT."""
    description = lire_description_grille(grille)
    source = generer_modele_q62(description, modele)
    compilation = compiler_modele(source, amo, repetitions_compilation)
    encoding = compilation.encoding
    formula = [frozenset(clause) for clause in encoding.clauses]
    profil = profil_clauses(encoding.clauses)
    communes = {
        "instance": grille.name,
        "taille": description.n,
        "modele": modele,
        "amo": amo,
        "heuristique": heuristique,
        "compilation_cpu_ms": f"{compilation.cpu_ms:.3f}",
        "contraintes_developpees": len(compilation.expanded.constraints),
        "avertissements": len(compilation.expanded.warnings),
        "variables": encoding.variable_count,
        "variables_nommees": len(encoding.id_to_name),
        "variables_auxiliaires": encoding.variable_count - len(encoding.id_to_name),
        "clauses": len(encoding.clauses),
        **profil,
    }

    lignes = []
    for repetition in range(repetitions):
        resultat = dpll_h_instrumente(
            formula, heuristique=heuristique, seed=repetition, limite_s=limite_s
        )
        stats = resultat.statistiques
        if resultat.satisfiable is None:
            statut = "TIMEOUT"
        elif not resultat.satisfiable:
            raise RuntimeError(
                f"{grille.name}, modele {modele} : UNSAT pour une grille attendue SAT"
            )
        else:
            statut = "SAT"
            valuation = {
                identifier: resultat.valuation.get(identifier, False)
                for identifier in range(1, encoding.variable_count + 1)
            }
            if not verifier_valuation(formula, valuation):
                raise RuntimeError(
                    f"{grille.name}, modele {modele} : valuation SAT invalide"
                )
            values = decode(encoding, valuation)
            solution = decoder_solution(description, modele, values)
            grid = [list(row) for row in description.grille]
            if not verifier_solution(grid, solution):
                raise RuntimeError(
                    f"{grille.name}, modele {modele} : solution Meowdoku invalide"
                )

        lignes.append({
            **communes,
            "repetition": repetition,
            "statut": statut,
            "decisions": stats.decisions,
            "retours_arriere": stats.retours_arriere,
            "propagations_unitaires": stats.propagations_unitaires,
            "litteraux_purs": stats.litteraux_purs,
            "noeuds": stats.noeuds,
            "profondeur_max": stats.profondeur_max,
            "resolution_cpu_ms": f"{stats.temps_cpu_ms:.3f}",
            "heuristique_cpu_ms": f"{stats.temps_heuristique_ms:.3f}",
            "ratio_heuristique": f"{stats.ratio_heuristique:.4f}",
        })
    return lignes


def _fmt(valeurs: list[float], decimales: int = 0) -> str:
    if not valeurs:
        return "-"
    return f"{median(valeurs):.{decimales}f}"


def resumer(lignes: list[dict[str, str]]) -> str:
    """Produit les tableaux Markdown de comparaison par taille et modele."""
    groupes: dict[tuple[int, str], list[dict[str, str]]] = {}
    for ligne in lignes:
        cle = (int(ligne["taille"]), ligne["modele"])
        groupes.setdefault(cle, []).append(ligne)

    texte = [
        "# Question 6.3 - comparaison des modèles Meowdoku",
        "",
        "Toutes les lignes utilisent le même compilateur, le même encodage de "
        "`atMostOne` et la même heuristique DPLL. Les valeurs sont des médianes ; "
        "les compteurs de recherche excluent les exécutions interrompues.",
        "",
        "| N | modèle | instances | SAT/exécutions | compilation (ms) | variables | "
        "clauses | binaires | résolution (ms) | décisions | retours | propagations |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    resumes = {}
    for cle in sorted(groupes):
        taille, modele = cle
        groupe = groupes[cle]
        terminees = [ligne for ligne in groupe if ligne["statut"] == "SAT"]
        instances = len({ligne["instance"] for ligne in groupe})

        def nombres(champ: str, source=groupe) -> list[float]:
            return [float(ligne[champ]) for ligne in source]

        clauses = nombres("clauses")
        binaires = nombres("clauses_binaires")
        ratio_binaires = [100 * b / c for b, c in zip(binaires, clauses) if c]
        resume = {
            "clauses": median(clauses),
            "resolution": median(nombres("resolution_cpu_ms", terminees)) if terminees else None,
            "decisions": median(nombres("decisions", terminees)) if terminees else None,
            "complet": len(terminees) == len(groupe),
        }
        resumes[cle] = resume
        texte.append(
            f"| {taille} | {modele} | {instances} | {len(terminees)}/{len(groupe)} "
            f"| {_fmt(nombres('compilation_cpu_ms'), 1)} "
            f"| {_fmt(nombres('variables'))} | {_fmt(clauses)} "
            f"| {_fmt(ratio_binaires, 1)}% "
            f"| {_fmt(nombres('resolution_cpu_ms', terminees), 1)} "
            f"| {_fmt(nombres('decisions', terminees))} "
            f"| {_fmt(nombres('retours_arriere', terminees))} "
            f"| {_fmt(nombres('propagations_unitaires', terminees))} |"
        )

    texte += [
        "",
        "## Ratios positions / cells",
        "",
        "Un ratio supérieur à 1 signifie que le modèle `positions` est plus grand "
        "ou plus coûteux pour la mesure concernée.",
        "",
        "| N | clauses | résolution | décisions |",
        "|---:|---:|---:|---:|",
    ]
    tailles = sorted({taille for taille, _ in groupes})
    for taille in tailles:
        positions = resumes.get((taille, "positions"))
        cells = resumes.get((taille, "cells"))
        if positions is None or cells is None:
            continue

        def ratio(champ: str, recherche: bool = True) -> str:
            if recherche and (not positions["complet"] or not cells["complet"]):
                return "-"
            numerateur, denominateur = positions[champ], cells[champ]
            if numerateur is None or denominateur in (None, 0):
                return "-"
            return f"{numerateur / denominateur:.2f}x"

        texte.append(
            f"| {taille} | {ratio('clauses', recherche=False)} | {ratio('resolution')} "
            f"| {ratio('decisions')} |"
        )
    texte += [
        "",
        "Les ratios de recherche ne sont pas calculés lorsqu'un des deux modèles "
        "a subi un timeout : les médianes ne porteraient alors pas sur les mêmes "
        "instances.",
        "",
        "## Interprétation",
        "",
        "Le compilateur et le solveur sont identiques, mais ils ne reçoivent pas "
        "la même FNC. Le modèle `positions` encode deux coordonnées de domaine "
        "`1..N` par région, soit `2N^2` variables SAT nommées. Ses contraintes de "
        "voisinage peuvent produire un nombre de clauses en ordre `N^4`. Le modèle "
        "`cells` utilise directement `N^2` booléens et, pour des régions équilibrées, "
        "un nombre de clauses plutôt en ordre `N^3`.",
        "",
        "La structure compte autant que la taille. Les clauses du modèle `cells` "
        "sont presque toutes binaires, tandis que `positions` contient beaucoup de "
        "clauses longues issues des quatre égalités de coordonnées. Cela modifie les "
        "propagations unitaires, l'ordre des choix et donc l'arbre DPLL.",
        "",
        "Enfin, une décision n'a pas un coût constant dans ce solveur : chaque "
        "affectation appelle `simplifier`, qui parcourt et recopie la formule "
        "courante. Une grande FNC peut donc prendre plus de temps avec moins de "
        "décisions. Les compteurs de recherche doivent toujours être lus avec le "
        "nombre et la longueur des clauses.",
        "",
    ]
    return "\n".join(texte)


def grilles_par_defaut(repertoire: Path, tailles: set[int]) -> list[Path]:
    """Selectionne les instances SAT de la question 5 aux tailles demandees."""
    grilles = []
    for grille in sorted(repertoire.glob("meow_sat_*_s*.txt")):
        description = lire_description_grille(grille)
        if description.n in tailles:
            grilles.append(grille)
    return grilles


def _ecrire_rapport(csv_path: Path, rapport_path: Path) -> None:
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rapport = resumer(list(csv.DictReader(stream)))
    rapport_path.parent.mkdir(parents=True, exist_ok=True)
    rapport_path.write_text(rapport, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commandes = parser.add_subparsers(dest="commande", required=True)

    mesure = commandes.add_parser("mesurer", help="compiler et resoudre les deux modeles")
    mesure.add_argument("grilles", nargs="*", type=Path)
    mesure.add_argument(
        "--repertoire",
        type=Path,
        default=RACINE / "partie_1/grilles/q5",
        help="repertoire des grilles utilise si aucune grille n'est donnee",
    )
    mesure.add_argument("--tailles", nargs="+", type=int, default=[6, 8, 10, 12, 14])
    mesure.add_argument("--amo", choices=("pairwise", "sinz"), default="pairwise")
    mesure.add_argument(
        "--heuristique", choices=TOUTES_HEURISTIQUES, default="h1"
    )
    mesure.add_argument("--repetitions", type=int, default=3)
    mesure.add_argument("--repetitions-compilation", type=int, default=3)
    mesure.add_argument("--limite", type=float, default=30.0)
    mesure.add_argument("--csv", type=Path, default=DOSSIER_Q63 / "resultats_q63.csv")
    mesure.add_argument("--rapport", type=Path, default=DOSSIER_Q63 / "rapport_q63.md")

    resume = commandes.add_parser("resumer", help="regenerer le rapport depuis le CSV")
    resume.add_argument("csv", type=Path)
    resume.add_argument("--rapport", type=Path)

    args = parser.parse_args()
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20_000))
    try:
        if args.commande == "resumer":
            with args.csv.open(encoding="utf-8", newline="") as stream:
                texte = resumer(list(csv.DictReader(stream)))
            if args.rapport is None:
                print(texte)
            else:
                args.rapport.parent.mkdir(parents=True, exist_ok=True)
                args.rapport.write_text(texte, encoding="utf-8")
                print(args.rapport)
            return 0

        if args.repetitions < 1 or args.repetitions_compilation < 1 or args.limite <= 0:
            parser.error("les repetitions et la limite doivent etre strictement positives")
        grilles = args.grilles or grilles_par_defaut(args.repertoire, set(args.tailles))
        if not grilles:
            parser.error("aucune grille SAT selectionnee")

        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLONNES)
            writer.writeheader()
            for grille in grilles:
                for modele in MODELES:
                    lignes = mesurer_modele(
                        grille,
                        modele,
                        amo=args.amo,
                        heuristique=args.heuristique,
                        repetitions=args.repetitions,
                        repetitions_compilation=args.repetitions_compilation,
                        limite_s=args.limite,
                    )
                    writer.writerows(lignes)
                    stream.flush()
                    statuts = ", ".join(str(ligne["statut"]) for ligne in lignes)
                    print(f"{grille.name} {modele}: {statuts}", file=sys.stderr)
        _ecrire_rapport(args.csv, args.rapport)
        print(f"CSV : {args.csv}")
        print(f"Rapport : {args.rapport}")
        return 0
    except (OSError, ValueError, RuntimeError, CompilationError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
