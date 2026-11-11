"""Compare les temps CPU des deux versions sur les mêmes graines aléatoires."""

import argparse
import csv
import json
from pathlib import Path
from statistics import median
import sys
from time import process_time_ns

if __package__:
    from .sat import dpll, dpll_valuation, lire_dimacs, verifier_valuation
else:
    from sat import dpll, dpll_valuation, lire_dimacs, verifier_valuation


def trouver_instances(cible: Path) -> list[Path]:
    """Renvoie le fichier demandé ou les instances public-*.cnf d'un dossier."""
    if cible.is_file():
        return [cible]
    if cible.is_dir():
        instances = sorted(cible.rglob("public-*.cnf"))
        if instances:
            return instances
        raise ValueError(f"Aucune instance public-*.cnf dans {cible}.")
    raise ValueError(f"Fichier ou dossier introuvable : {cible}.")


def lire_resultats_attendus(cible: Path) -> dict[str, str]:
    """Lit expected.json lorsqu'il existe dans le dossier public fourni."""
    candidats = [cible / "expected.json"] if cible.is_dir() else []
    candidats.extend(parent / "expected.json" for parent in cible.parents)
    for chemin in candidats:
        if chemin.is_file():
            contenu = json.loads(chemin.read_text(encoding="utf-8"))
            if not isinstance(contenu, dict):
                raise ValueError(f"Format invalide dans {chemin}.")
            return {str(nom): str(statut) for nom, statut in contenu.items()}
    return {}


def mesurer_instance(
    instance: Path, repetitions: int, attendu: str | None
) -> list[list[str | int]]:
    """Mesure les deux solveurs sur une instance et produit deux lignes CSV."""
    n, formule = lire_dimacs(instance)
    durees: dict[int, list[float]] = {1: [], 2: []}
    statuts: set[bool] = set()
    for seed in range(repetitions):
        # Alterner l'ordre pour limiter un biais lié à l'ordre d'exécution.
        for version in ((1, 2) if seed % 2 == 0 else (2, 1)):
            solveur = dpll if version == 1 else dpll_valuation
            debut = process_time_ns()
            resultat = solveur(formule, seed=seed)
            durees[version].append((process_time_ns() - debut) / 1_000_000)
            statut = resultat if version == 1 else resultat[0]
            statuts.add(statut)
            if version == 2 and statut and not verifier_valuation(formule, resultat[1]):
                raise RuntimeError(f"Modèle invalide pour {instance}.")

    if len(statuts) != 1:
        raise RuntimeError(f"Les solveurs divergent sur {instance}.")
    statut = "SAT" if statuts.pop() else "UNSAT"
    if attendu is not None and statut != attendu:
        raise RuntimeError(
            f"Résultat incorrect pour {instance.name} : {statut}, attendu {attendu}."
        )

    return [
        [
            str(instance), n, len(formule), version, repetitions, statut,
            f"{median(temps):.6f}", f"{min(temps):.6f}", f"{max(temps):.6f}",
        ]
        for version, temps in durees.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cible",
        type=Path,
        help="Fichier DIMACS ou dossier contenant les instances public-*.cnf",
    )
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument(
        "--limite",
        type=int,
        help="Nombre maximal d'instances du dossier à mesurer",
    )
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("Le nombre de répétitions doit être strictement positif.")
    if args.limite is not None and args.limite < 1:
        parser.error("La limite doit être strictement positive.")
    try:
        instances = trouver_instances(args.cible)
        if args.limite is not None:
            instances = instances[:args.limite]
        attendus = lire_resultats_attendus(args.cible)
    except (OSError, ValueError, json.JSONDecodeError) as erreur:
        parser.error(str(erreur))

    sortie = csv.writer(sys.stdout)
    sortie.writerow(["instance", "variables", "clauses", "version", "repetitions",
                     "statut", "cpu_mediane_ms", "cpu_min_ms", "cpu_max_ms"])
    try:
        for instance in instances:
            for ligne in mesurer_instance(
                instance, args.repetitions, attendus.get(instance.name)
            ):
                sortie.writerow(ligne)
    except (OSError, ValueError, RuntimeError) as erreur:
        parser.error(str(erreur))


if __name__ == "__main__":
    main()
