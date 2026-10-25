"""Évalue les solveurs Q6 via leur interface finale et valide leurs modèles."""

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import TextIO, TypeAlias

RACINE = Path(__file__).resolve().parent.parent
if __package__ in (None, ""):
    sys.path.insert(0, str(RACINE))

from question2.sat import Valuation, lire_dimacs, verifier_valuation  # noqa: E402


Instance: TypeAlias = tuple[Path, str, bool]
SOLVEURS: tuple[str, ...] = (
    "dpll",
    "optimized-h1",
    "optimized-h4",
    "optimized-adaptive",
)
COLONNES: tuple[str, ...] = (
    "instance", "famille", "variables", "clauses", "attendu",
    "solveur", "statut", "correct", "secondes",
)


def lister_instances(dossier_public: Path, dossier_meowdoku: Path) -> list[Instance]:
    """Réunit les 30 instances publiques et les 25 instances Meowdoku."""
    attendus: dict[str, str] = json.loads(
        (dossier_public / "expected.json").read_text(encoding="utf-8")
    )
    instances: list[Instance] = [
        (chemin, "public", attendus[chemin.name] == "SAT")
        for chemin in sorted((dossier_public / "instances").glob("public-*.cnf"))
    ]
    grille = dossier_meowdoku.parent / "grille.cnf"
    if grille.is_file():
        instances.append((grille, "meowdoku", True))
    instances.extend(
        (chemin, "meowdoku", "_unsat_" not in chemin.name)
        for chemin in sorted(dossier_meowdoku.glob("meow_*.cnf"))
    )
    return instances


def analyser_sortie(
    sortie: str, nombre_variables: int
) -> tuple[bool, Valuation | None]:
    """Interprète strictement le statut et le modèle produits par ``sat.py``."""
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


def commande(chemin: Path, solveur: str) -> list[str]:
    """Construit la commande finale correspondant à une variante mesurée."""
    arguments = [
        sys.executable, str(RACINE / "sat.py"), str(chemin), "--output-model",
    ]
    if solveur == "dpll":
        return [*arguments, "--mode", "dpll", "--seed", "0"]
    strategie = solveur.removeprefix("optimized-")
    return [
        *arguments, "--mode", "optimized", "--strategie",
        "auto" if strategie == "adaptive" else strategie,
    ]


def mesurer(
    instances: list[Instance],
    solveurs: list[str],
    limite_s: float,
    sortie: TextIO,
) -> None:
    """Mesure les exécutions complètes et écrit une ligne CSV par essai."""
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(COLONNES)
    for chemin, famille, attendu in instances:
        nombre_variables, formule = lire_dimacs(chemin)
        for solveur in solveurs:
            debut = perf_counter()
            try:
                resultat = subprocess.run(
                    commande(chemin, solveur), capture_output=True, text=True,
                    timeout=limite_s, check=True,
                )
                if resultat.stderr:
                    raise ValueError("Le solveur a écrit sur stderr.")
                satisfiable, valuation = analyser_sortie(
                    resultat.stdout, nombre_variables
                )
                correct = satisfiable == attendu and (
                    not satisfiable or verifier_valuation(formule, valuation or {})
                )
                statut = "SAT" if satisfiable else "UNSAT"
            except subprocess.TimeoutExpired:
                statut, correct = "TIMEOUT", False
            except (subprocess.SubprocessError, ValueError):
                statut, correct = "ERROR", False
            duree = perf_counter() - debut
            ecrivain.writerow((
                chemin.name, famille, nombre_variables, len(formule),
                "SAT" if attendu else "UNSAT", solveur, statut,
                int(correct), f"{duree:.6f}",
            ))
            sortie.flush()
            print(
                f"{chemin.name} {solveur}: {statut} ({duree:.3f} s)",
                file=sys.stderr,
            )


def resumer(lignes: list[dict[str, str]]) -> str:
    """Produit un tableau Markdown par famille à partir du CSV brut."""
    textes: list[str] = []
    solveurs = list(dict.fromkeys(ligne["solveur"] for ligne in lignes))
    for famille in ("public", "meowdoku", "total"):
        selection = [
            ligne for ligne in lignes
            if famille == "total" or ligne["famille"] == famille
        ]
        textes.extend((
            f"### {famille}", "",
            "| Solveur | Correctes | SAT | UNSAT | Timeouts | Temps correct (s) |",
            "|---|---:|---:|---:|---:|---:|",
        ))
        for solveur in solveurs:
            groupe = [ligne for ligne in selection if ligne["solveur"] == solveur]
            correctes = [ligne for ligne in groupe if ligne["correct"] == "1"]
            sat = sum(ligne["attendu"] == "SAT" for ligne in correctes)
            unsat = sum(ligne["attendu"] == "UNSAT" for ligne in correctes)
            timeouts = sum(ligne["statut"] == "TIMEOUT" for ligne in groupe)
            temps = sum(float(ligne["secondes"]) for ligne in correctes)
            textes.append(
                f"| {solveur} | {len(correctes)}/{len(groupe)} | {sat} | "
                f"{unsat} | {timeouts} | {temps:.3f} |"
            )
        textes.append("")
    return "\n".join(textes)


def main() -> None:
    """Lance une mesure ou résume un fichier de résultats existant."""
    parser = argparse.ArgumentParser(description=__doc__)
    commandes = parser.add_subparsers(dest="commande", required=True)
    mesure = commandes.add_parser("mesurer")
    mesure.add_argument("--public", type=Path, default=RACINE / "public-instances")
    mesure.add_argument("--meowdoku", type=Path, default=RACINE / "instances/q5")
    mesure.add_argument(
        "--solveurs", nargs="+", choices=SOLVEURS, default=list(SOLVEURS)
    )
    mesure.add_argument("--limite", type=float, default=60.0)
    mesure.add_argument("--filtre")
    resume = commandes.add_parser("resumer")
    resume.add_argument("csv", type=Path)
    args = parser.parse_args()

    if args.commande == "mesurer":
        if args.limite <= 0:
            parser.error("--limite doit être strictement positive.")
        instances = lister_instances(args.public, args.meowdoku)
        if args.filtre:
            instances = [
                instance for instance in instances
                if args.filtre in instance[0].name
            ]
        mesurer(instances, args.solveurs, args.limite, sys.stdout)
    else:
        with args.csv.open(encoding="utf-8") as fichier:
            print(resumer(list(csv.DictReader(fichier))))


if __name__ == "__main__":
    main()
