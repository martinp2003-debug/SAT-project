"""Mesure et compare les heuristiques de DPLL_H (question 5).

Deux usages :

- ``mesurer`` exécute chaque heuristique sur les instances et écrit un CSV
  contenant une ligne par exécution ;
- ``resumer`` relit ce CSV et produit des tableaux Markdown agrégés,
  séparément pour les instances SAT et UNSAT.
"""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import mean, median
import sys
from typing import TextIO


# Permet aussi l'exécution directe : python3 question5/benchmark_q5.py ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from question2.sat import lire_dimacs, verifier_valuation  # noqa: E402
from question5.instrumentation import (  # noqa: E402
    TOUTES_HEURISTIQUES,
    dpll_h_instrumente,
)


COLONNES = [
    "instance", "famille", "variables", "clauses", "attendu", "heuristique",
    "seed", "statut", "decisions", "retours_arriere", "propagations_unitaires",
    "litteraux_purs", "noeuds", "profondeur_max", "cpu_ms", "heuristique_ms",
    "ratio_heuristique",
]


def lister_instances(public: Path, meowdoku: Path) -> list[tuple[Path, str, str]]:
    """Renvoie ``(chemin, famille, statut attendu)`` pour chaque instance."""
    instances = []
    attendus = json.loads((public / "expected.json").read_text(encoding="utf-8"))
    for chemin in sorted((public / "instances").glob("public-*.cnf")):
        instances.append((chemin, "public", attendus[chemin.name]))
    grille = meowdoku.parent / "grille.cnf"
    if grille.is_file():
        instances.append((grille, "meowdoku", "SAT"))
    for chemin in sorted(meowdoku.glob("meow_*.cnf")):
        attendu = "UNSAT" if "_unsat_" in chemin.name else "SAT"
        instances.append((chemin, "meowdoku", attendu))
    return instances


def mesurer(
    instances: list[tuple[Path, str, str]],
    heuristiques: list[str],
    graines_h0: int,
    limite_s: float,
    sortie: TextIO,
) -> None:
    """Exécute toutes les combinaisons et écrit une ligne CSV par exécution.

    H0 étant aléatoire, il est exécuté avec plusieurs graines ; les autres
    heuristiques sont déterministes et ne sont exécutées qu'une fois.
    """
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(COLONNES)
    for chemin, famille, attendu in instances:
        n, formule = lire_dimacs(chemin)
        for heuristique in heuristiques:
            graines = range(graines_h0) if heuristique == "h0" else [0]
            for seed in graines:
                resultat = dpll_h_instrumente(formule, heuristique, seed, limite_s)
                s = resultat.statistiques
                if resultat.satisfiable is None:
                    statut = "TIMEOUT"
                else:
                    statut = "SAT" if resultat.satisfiable else "UNSAT"
                    if statut != attendu:
                        raise RuntimeError(
                            f"{chemin.name}, {heuristique} : {statut} au lieu de {attendu}."
                        )
                    if resultat.satisfiable and not verifier_valuation(
                        formule, resultat.valuation
                    ):
                        raise RuntimeError(f"Modèle invalide : {chemin.name}, {heuristique}.")
                ecrivain.writerow([
                    chemin.name, famille, n, len(formule), attendu, heuristique,
                    seed, statut, s.decisions, s.retours_arriere,
                    s.propagations_unitaires, s.litteraux_purs, s.noeuds,
                    s.profondeur_max, f"{s.temps_cpu_ms:.3f}",
                    f"{s.temps_heuristique_ms:.3f}", f"{s.ratio_heuristique:.4f}",
                ])
                sortie.flush()
                print(f"{chemin.name} {heuristique} seed={seed} {statut} "
                      f"{s.temps_cpu_ms:.0f} ms", file=sys.stderr)


def _lignes_par_instance(lignes: list[dict[str, str]]) -> dict[tuple[str, str], dict]:
    """Agrège les graines de H0 : médiane des mesures, résolu si toutes le sont."""
    groupes: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for ligne in lignes:
        groupes[ligne["instance"], ligne["heuristique"]].append(ligne)
    agreges = {}
    for cle, groupe in groupes.items():
        agreges[cle] = {
            "famille": groupe[0]["famille"],
            "attendu": groupe[0]["attendu"],
            "resolu": all(g["statut"] != "TIMEOUT" for g in groupe),
            **{
                champ: median(float(g[champ]) for g in groupe)
                for champ in ("decisions", "retours_arriere", "propagations_unitaires",
                              "litteraux_purs", "cpu_ms", "ratio_heuristique")
            },
        }
    return agreges


def resumer(lignes: list[dict[str, str]], heuristiques: list[str]) -> str:
    """Produit les tableaux Markdown du rapport à partir des lignes du CSV."""
    agreges = _lignes_par_instance(lignes)
    instances = sorted({instance for instance, _ in agreges})
    textes = []
    for famille in ("public", "meowdoku", None):
        for attendu in ("SAT", "UNSAT"):
            selection = [
                i for i in instances
                if agreges[i, heuristiques[0]]["attendu"] == attendu
                and (famille is None or agreges[i, heuristiques[0]]["famille"] == famille)
            ]
            if not selection:
                continue
            communes = [
                i for i in selection if all(agreges[i, h]["resolu"] for h in heuristiques)
            ]
            titre = "toutes familles" if famille is None else famille
            textes.append(
                f"### {titre} — {attendu} ({len(selection)} instances, "
                f"{len(communes)} résolues par toutes les heuristiques)\n"
            )
            textes.append(
                "| H | résolues | CPU total communes (ms) | décisions | retours "
                "| propag. unitaires | littéraux purs | ratio heuristique |"
            )
            textes.append("|---|---|---|---|---|---|---|---|")
            for h in heuristiques:
                resolues = sum(agreges[i, h]["resolu"] for i in selection)

                def total(champ: str) -> float:
                    return sum(agreges[i, h][champ] for i in communes)

                ratio = mean(agreges[i, h]["ratio_heuristique"] for i in communes) if communes else 0
                textes.append(
                    f"| {h} | {resolues}/{len(selection)} | {total('cpu_ms'):.0f} "
                    f"| {total('decisions'):.0f} | {total('retours_arriere'):.0f} "
                    f"| {total('propagations_unitaires'):.0f} "
                    f"| {total('litteraux_purs'):.0f} | {ratio:.0%} |"
                )
            textes.append("")
    return "\n".join(textes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commandes = parser.add_subparsers(dest="commande", required=True)

    p_mesure = commandes.add_parser("mesurer", help="Exécuter les mesures")
    p_mesure.add_argument("--public", type=Path, default=Path("public-instances"))
    p_mesure.add_argument("--meowdoku", type=Path, default=Path("instances/q5"))
    p_mesure.add_argument(
        "--heuristiques", nargs="+", choices=TOUTES_HEURISTIQUES,
        default=list(TOUTES_HEURISTIQUES),
    )
    p_mesure.add_argument("--graines-h0", type=int, default=3)
    p_mesure.add_argument(
        "--limite", type=float, default=10.0, help="Temps CPU maximal par exécution (s)"
    )
    p_mesure.add_argument("--filtre", help="Ne garder que les instances contenant ce texte")

    p_resume = commandes.add_parser("resumer", help="Résumer un CSV de mesures")
    p_resume.add_argument("csv", type=Path)

    args = parser.parse_args()
    # La profondeur de récursion peut atteindre le nombre de variables.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 20_000))
    if args.commande == "mesurer":
        if args.graines_h0 < 1 or args.limite <= 0:
            parser.error("--graines-h0 et --limite doivent être strictement positifs.")
        instances = lister_instances(args.public, args.meowdoku)
        if args.filtre:
            instances = [i for i in instances if args.filtre in i[0].name]
        mesurer(instances, args.heuristiques, args.graines_h0, args.limite, sys.stdout)
    else:
        with args.csv.open(encoding="utf-8") as fichier:
            lignes = list(csv.DictReader(fichier))
        presentes = list(dict.fromkeys(l["heuristique"] for l in lignes))
        print(resumer(lignes, presentes))


if __name__ == "__main__":
    main()
