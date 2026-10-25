"""Compare les deux modes via l'interface finale de la question 6."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import TextIO

RACINE = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(RACINE))

from question2.sat import Valuation, lire_dimacs, verifier_valuation  # noqa: E402


MODES: tuple[str, ...] = ("dpll", "optimized")


def lister_instances(dossier: Path) -> list[tuple[Path, bool]]:
    """Liste les instances publiques accompagnées de leur statut attendu."""
    attendus: dict[str, str] = json.loads(
        (dossier / "expected.json").read_text(encoding="utf-8")
    )
    return [
        (chemin, attendus[chemin.name] == "SAT")
        for chemin in sorted((dossier / "instances").glob("public-*.cnf"))
    ]


def analyser_sortie(
    sortie: str, nombre_variables: int
) -> tuple[bool, Valuation | None]:
    """Interprète le statut et l'éventuel modèle produits par ``sat.py``."""
    lignes = sortie.splitlines()
    if not lignes or lignes[0] not in ("s SATISFIABLE", "s UNSATISFIABLE"):
        raise ValueError("Format de statut invalide.")
    satisfiable = lignes[0] == "s SATISFIABLE"
    if not satisfiable:
        if len(lignes) != 1:
            raise ValueError("Une réponse UNSAT ne doit pas contenir de modèle.")
        return False, None
    if len(lignes) != 2:
        raise ValueError("Modèle SAT manquant ou sortie supplémentaire.")
    mots = lignes[1].split()
    if len(mots) != nombre_variables + 2 or mots[0] != "v" or mots[-1] != "0":
        raise ValueError("Format du modèle invalide.")
    litteraux = [int(mot) for mot in mots[1:-1]]
    if [abs(litteral) for litteral in litteraux] != list(
        range(1, nombre_variables + 1)
    ):
        raise ValueError("Le modèle doit affecter chaque variable une fois.")
    return True, {abs(litteral): litteral > 0 for litteral in litteraux}


def mesurer(
    instances: list[tuple[Path, bool]],
    modes: list[str],
    limite_s: float,
    sortie: TextIO,
) -> None:
    """Exécute l'interface finale et écrit une ligne CSV par essai."""
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(("instance", "mode", "statut", "correct", "secondes"))
    for chemin, attendu in instances:
        nombre_variables, formule = lire_dimacs(chemin)
        for mode in modes:
            debut = perf_counter()
            try:
                resultat = subprocess.run(
                    [
                        sys.executable,
                        str(RACINE / "sat.py"),
                        str(chemin),
                        "--mode",
                        mode,
                        "--output-model",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=limite_s,
                    check=True,
                )
                satisfiable, valuation = analyser_sortie(
                    resultat.stdout, nombre_variables
                )
                correct = satisfiable == attendu and (
                    not satisfiable
                    or verifier_valuation(formule, valuation or {})
                )
                statut = "SAT" if satisfiable else "UNSAT"
            except (subprocess.SubprocessError, ValueError):
                statut, correct = "TIMEOUT_OR_ERROR", False
            duree = perf_counter() - debut
            ecrivain.writerow(
                (chemin.name, mode, statut, int(correct), f"{duree:.6f}")
            )
            sortie.flush()


def main() -> None:
    """Analyse les options et lance le benchmark reproductible."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public", type=Path, default=RACINE / "public-instances"
    )
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--limite", type=float, default=60.0)
    parser.add_argument("--filtre")
    args = parser.parse_args()
    if args.limite <= 0:
        parser.error("--limite doit être strictement positive.")
    instances = lister_instances(args.public)
    if args.filtre:
        instances = [
            instance
            for instance in instances
            if args.filtre in instance[0].name
        ]
    mesurer(instances, args.modes, args.limite, sys.stdout)


if __name__ == "__main__":
    main()
