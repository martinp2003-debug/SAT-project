"""Mesure l'effet de la contrainte redondante de la question 6.4.

Le modèle ``cells`` est compilé et résolu dans deux variantes qui ne
diffèrent que par les clauses "au moins un chat par région". Une ligne CSV
correspond à une répétition du solveur sur un couple (grille, variante).
"""

import argparse
import csv
from pathlib import Path
from statistics import median
import sys


DOSSIER_Q64 = Path(__file__).resolve().parent
PARTIE_2 = DOSSIER_Q64.parent
RACINE = PARTIE_2.parent
PARTIE_1 = RACINE / "partie_1"
DOSSIER_Q63 = PARTIE_2 / "question6.3"
for dossier in (PARTIE_2, PARTIE_1, DOSSIER_Q63):
    if str(dossier) not in sys.path:
        sys.path.insert(0, str(dossier))

from benchmark_q63 import (  # noqa: E402
    compiler_modele,
    grilles_par_defaut,
    profil_clauses,
)
from diagnostics import CompilationError  # noqa: E402
from encoding import decode  # noqa: E402
from meowdoku import (  # noqa: E402
    decoder_solution,
    generer_modele_q62,
    lire_description_grille,
)
from question2.sat import verifier_valuation  # noqa: E402
from question3.solution import verifier_solution  # noqa: E402
from question5.instrumentation import (  # noqa: E402
    TOUTES_HEURISTIQUES,
    dpll_h_instrumente,
)
from syntax import parse  # noqa: E402


VARIANTES = (("sans", False), ("avec", True))
COLONNES = [
    "instance", "taille", "variante", "amo", "heuristique", "repetition",
    "statut", "compilation_cpu_ms", "contraintes_developpees", "avertissements",
    "variables", "variables_nommees", "variables_auxiliaires", "clauses",
    "clauses_unitaires", "clauses_binaires", "clauses_ternaires",
    "clauses_longues", "occurrences_litteraux", "decisions", "retours_arriere",
    "propagations_unitaires", "litteraux_purs", "noeuds", "profondeur_max",
    "resolution_cpu_ms", "heuristique_cpu_ms", "ratio_heuristique",
]


def mesurer_variante(
    grille: Path,
    redundant_regions: bool,
    amo: str = "pairwise",
    heuristique: str = "h1",
    repetitions: int = 3,
    repetitions_compilation: int = 3,
    limite_s: float = 30.0,
) -> list[dict[str, object]]:
    """Compile, résout et vérifie une variante du modèle ``cells``."""
    description = lire_description_grille(grille)
    variante = "avec" if redundant_regions else "sans"
    source = generer_modele_q62(
        description, "cells", redundant_regions=redundant_regions
    )
    compilation = compiler_modele(source, amo, repetitions_compilation)
    encoding = compilation.encoding
    formula = [frozenset(clause) for clause in encoding.clauses]
    profil = profil_clauses(encoding.clauses)
    communes = {
        "instance": grille.name,
        "taille": description.n,
        "variante": variante,
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
                f"{grille.name}, variante {variante} : "
                "UNSAT pour une grille attendue SAT"
            )
        else:
            statut = "SAT"
            valuation = {
                identifier: resultat.valuation.get(identifier, False)
                for identifier in range(1, encoding.variable_count + 1)
            }
            if not verifier_valuation(formula, valuation):
                raise RuntimeError(
                    f"{grille.name}, variante {variante} : valuation SAT invalide"
                )
            values = decode(encoding, valuation)
            solution = decoder_solution(description, "cells", values)
            grid = [list(row) for row in description.grille]
            if not verifier_solution(grid, solution):
                raise RuntimeError(
                    f"{grille.name}, variante {variante} : "
                    "solution Meowdoku invalide"
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
    """Produit le rapport Markdown de comparaison avec/sans redondance."""
    groupes: dict[tuple[int, str], list[dict[str, str]]] = {}
    for ligne in lignes:
        cle = (int(ligne["taille"]), ligne["variante"])
        groupes.setdefault(cle, []).append(ligne)

    texte = [
        "# Question 6.4 - contrainte redondante par région",
        "",
        "Le modèle `cells` est mesuré avec et sans une clause "
        "`atLeastOne` par région. Le compilateur, l'encodage `pairwise`, "
        "l'heuristique DPLL et les instances restent identiques. Les valeurs "
        "sont des médianes ; les compteurs de recherche excluent les timeouts.",
        "",
        "| N | variante | instances | SAT/exécutions | compilation (ms) | "
        "variables | clauses | longues | résolution (ms) | décisions | "
        "retours | propagations |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    resumes = {}
    for cle in sorted(groupes):
        taille, variante = cle
        groupe = groupes[cle]
        terminees = [ligne for ligne in groupe if ligne["statut"] == "SAT"]

        def nombres(champ: str, source=groupe) -> list[float]:
            return [float(ligne[champ]) for ligne in source]

        resume = {
            "variables": median(nombres("variables")),
            "clauses": median(nombres("clauses")),
            "resolution": median(nombres("resolution_cpu_ms", terminees))
            if terminees else None,
            "decisions": median(nombres("decisions", terminees))
            if terminees else None,
            "retours": median(nombres("retours_arriere", terminees))
            if terminees else None,
            "complet": len(terminees) == len(groupe),
        }
        resumes[cle] = resume
        texte.append(
            f"| {taille} | {variante} | "
            f"{len({ligne['instance'] for ligne in groupe})} "
            f"| {len(terminees)}/{len(groupe)} "
            f"| {_fmt(nombres('compilation_cpu_ms'), 1)} "
            f"| {_fmt(nombres('variables'))} | {_fmt(nombres('clauses'))} "
            f"| {_fmt(nombres('clauses_longues'))} "
            f"| {_fmt(nombres('resolution_cpu_ms', terminees), 1)} "
            f"| {_fmt(nombres('decisions', terminees))} "
            f"| {_fmt(nombres('retours_arriere', terminees))} "
            f"| {_fmt(nombres('propagations_unitaires', terminees))} |"
        )

    texte += [
        "",
        "## Effet de la contrainte redondante",
        "",
        "Le gain est le ratio `sans / avec` : une valeur supérieure à 1 "
        "indique que la variante redondante demande moins de temps ou de recherche.",
        "",
        "| N | Δ variables | Δ clauses | gain résolution | gain décisions | "
        "gain retours |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    tailles = sorted({taille for taille, _ in groupes})
    gains_resolution = []
    for taille in tailles:
        sans = resumes.get((taille, "sans"))
        avec = resumes.get((taille, "avec"))
        if sans is None or avec is None:
            continue

        def gain(champ: str) -> str:
            if not sans["complet"] or not avec["complet"]:
                return "-"
            numerateur, denominateur = sans[champ], avec[champ]
            if numerateur is None or denominateur in (None, 0):
                return "-"
            return f"{numerateur / denominateur:.2f}x"

        texte.append(
            f"| {taille} | {avec['variables'] - sans['variables']:.0f} "
            f"| {avec['clauses'] - sans['clauses']:.0f} "
            f"| {gain('resolution')} | {gain('decisions')} | {gain('retours')} |"
        )
        if (
            sans["complet"] and avec["complet"]
            and sans["resolution"] is not None
            and avec["resolution"] not in (None, 0)
        ):
            gains_resolution.append(
                (taille, sans["resolution"] / avec["resolution"])
            )

    if gains_resolution:
        accelerations = sum(gain > 1 for _, gain in gains_resolution)
        minimum = min(gain for _, gain in gains_resolution)
        maximum = max(gain for _, gain in gains_resolution)
        nombre_tailles = len(gains_resolution)
        tailles = "taille" if nombre_tailles == 1 else "tailles"
        mesurees = "mesurée" if nombre_tailles == 1 else "mesurées"
        texte += [
            "",
            f"Dans cette campagne, la variante redondante est plus rapide pour "
            f"{accelerations} {tailles} sur {nombre_tailles} {mesurees}. "
            f"Le gain médian selon la taille va de {minimum:.2f}x à "
            f"{maximum:.2f}x.",
        ]

    texte += [
        "",
        "Les gains de recherche ne sont pas calculés si une variante subit un "
        "timeout, car les médianes ne porteraient plus sur les mêmes exécutions.",
        "",
        "## Interprétation",
        "",
        "Il y a exactement `N` chats grâce aux contraintes de lignes et `K=N` "
        "régions contenant chacune au plus un chat. Par le principe des tiroirs, "
        "chaque région contient donc déjà un chat : les nouvelles clauses ne "
        "changent pas l'ensemble des solutions.",
        "",
        "La variante `avec` ajoute une grande disjonction par région, donc `K` "
        "clauses et aucune variable SAT. Ces clauses peuvent détecter plus tôt "
        "qu'une région n'a plus qu'une case possible et provoquer une propagation "
        "unitaire. Elles peuvent ainsi réduire les décisions et retours arrière.",
        "",
        "Ce renforcement n'est pas gratuit : le DPLL de référence parcourt et "
        "recopie la formule pendant la simplification. Les clauses longues ajoutent "
        "donc du travail à chaque affectation. Les temps doivent être interprétés "
        "avec les compteurs de recherche, et non comme une garantie générale "
        "qu'une contrainte redondante accélère SAT.",
        "",
    ]
    return "\n".join(texte)


def _ecrire_rapport(csv_path: Path, rapport_path: Path) -> None:
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rapport = resumer(list(csv.DictReader(stream)))
    rapport_path.parent.mkdir(parents=True, exist_ok=True)
    rapport_path.write_text(rapport, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commandes = parser.add_subparsers(dest="commande", required=True)

    mesure = commandes.add_parser("mesurer", help="comparer les deux variantes")
    mesure.add_argument("grilles", nargs="*", type=Path)
    mesure.add_argument(
        "--repertoire",
        type=Path,
        default=RACINE / "partie_1/grilles/q5",
        help="répertoire des grilles utilisé si aucune grille n'est donnée",
    )
    mesure.add_argument("--tailles", nargs="+", type=int, default=[6, 8, 10, 12, 14])
    mesure.add_argument("--amo", choices=("pairwise", "sinz"), default="pairwise")
    mesure.add_argument("--heuristique", choices=TOUTES_HEURISTIQUES, default="h1")
    mesure.add_argument("--repetitions", type=int, default=3)
    mesure.add_argument("--repetitions-compilation", type=int, default=3)
    mesure.add_argument("--limite", type=float, default=30.0)
    mesure.add_argument("--csv", type=Path, default=DOSSIER_Q64 / "resultats_q64.csv")
    mesure.add_argument(
        "--rapport", type=Path, default=DOSSIER_Q64 / "rapport_q64.md"
    )

    resume = commandes.add_parser("resumer", help="régénérer le rapport")
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
            parser.error("les répétitions et la limite doivent être strictement positives")
        grilles = args.grilles or grilles_par_defaut(args.repertoire, set(args.tailles))
        if not grilles:
            parser.error("aucune grille SAT sélectionnée")

        toutes_lignes = []
        for grille in grilles:
            for variante, redundant_regions in VARIANTES:
                lignes = mesurer_variante(
                    grille,
                    redundant_regions,
                    amo=args.amo,
                    heuristique=args.heuristique,
                    repetitions=args.repetitions,
                    repetitions_compilation=args.repetitions_compilation,
                    limite_s=args.limite,
                )
                toutes_lignes.extend(lignes)
                statuts = ", ".join(str(ligne["statut"]) for ligne in lignes)
                print(f"{grille.name} {variante}: {statuts}", file=sys.stderr)

        # Une seule écriture évite que la synchronisation OneDrive interfère
        # avec les mesures ou provoque un timeout entre deux instances.
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLONNES)
            writer.writeheader()
            writer.writerows(toutes_lignes)
        _ecrire_rapport(args.csv, args.rapport)
        print(f"CSV : {args.csv}")
        print(f"Rapport : {args.rapport}")
        return 0
    except (OSError, ValueError, RuntimeError, CompilationError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
