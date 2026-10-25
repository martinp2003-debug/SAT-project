"""Affectations, littéraux surveillés et retour arrière."""

from question2.sat import Litteral
from question6.structures import EtatSolveur, ProblemeCNF, Valeur


def indice_litteral(litteral: Litteral) -> int:
    """Associe un littéral non nul à un indice compact."""
    if litteral == 0:
        raise ValueError("Le littéral DIMACS 0 n'est pas une variable.")
    return 2 * (abs(litteral) - 1) + int(litteral < 0)


def valeur_litteral(etat: EtatSolveur, litteral: Litteral) -> Valeur:
    """Renvoie 1 si le littéral est vrai, 0 s'il est faux, -1 sinon."""
    valeur = etat.affectations[abs(litteral)]
    if valeur == -1:
        return -1
    return int(valeur == int(litteral > 0))


def affecter(etat: EtatSolveur, litteral: Litteral) -> bool:
    """Rend un littéral vrai et l'ajoute au trail, ou signale un conflit."""
    variable = abs(litteral)
    valeur: Valeur = 1 if litteral > 0 else 0
    actuelle = etat.affectations[variable]
    if actuelle == -1:
        etat.affectations[variable] = valeur
        etat.trail.append(litteral)
        return True
    return actuelle == valeur


def initialiser_etat(probleme: ProblemeCNF) -> EtatSolveur:
    """Crée les listes de surveillance et affecte les clauses unitaires."""
    etat = EtatSolveur(
        probleme=probleme,
        affectations=[-1] * (probleme.nombre_variables + 1),
        surveillances=[[] for _ in range(2 * probleme.nombre_variables)],
    )
    unites: list[Litteral] = []
    for numero, clause in enumerate(probleme.clauses):
        if not clause:
            etat.positions_surveillees.append((0, 0))
            etat.conflit_initial = True
            continue
        seconde = 0 if len(clause) == 1 else 1
        etat.positions_surveillees.append((0, seconde))
        etat.surveillances[indice_litteral(clause[0])].append(numero)
        if seconde != 0:
            etat.surveillances[indice_litteral(clause[seconde])].append(numero)
        else:
            unites.append(clause[0])

    for litteral in unites:
        if not affecter(etat, litteral):
            etat.conflit_initial = True
    return etat


def propager(etat: EtatSolveur) -> bool:
    """Propage les unités avec deux littéraux surveillés par clause."""
    if etat.conflit_initial:
        return False
    while etat.prochain_a_propager < len(etat.trail):
        litteral_vrai = etat.trail[etat.prochain_a_propager]
        etat.prochain_a_propager += 1
        litteral_faux = -litteral_vrai
        surveillees = etat.surveillances[indice_litteral(litteral_faux)]
        index = 0
        while index < len(surveillees):
            numero_clause = surveillees[index]
            clause = etat.probleme.clauses[numero_clause]
            premiere, seconde = etat.positions_surveillees[numero_clause]

            if clause[premiere] == litteral_faux:
                position_fausse, position_autre = premiere, seconde
                premiere_est_fausse = True
            else:
                position_fausse, position_autre = seconde, premiere
                premiere_est_fausse = False

            autre = clause[position_autre]
            if valeur_litteral(etat, autre) == 1:
                index += 1
                continue

            remplacement: int | None = None
            for position, candidat in enumerate(clause):
                if position in (position_fausse, position_autre):
                    continue
                if valeur_litteral(etat, candidat) != 0:
                    remplacement = position
                    break

            if remplacement is not None:
                if premiere_est_fausse:
                    etat.positions_surveillees[numero_clause] = (remplacement, seconde)
                else:
                    etat.positions_surveillees[numero_clause] = (premiere, remplacement)
                surveillees[index] = surveillees[-1]
                surveillees.pop()
                nouveau = clause[remplacement]
                etat.surveillances[indice_litteral(nouveau)].append(numero_clause)
                continue

            valeur_autre = valeur_litteral(etat, autre)
            if valeur_autre == 0 or not affecter(etat, autre):
                return False
            index += 1
    return True


def ouvrir_niveau(etat: EtatSolveur) -> None:
    """Mémorise le début d'un niveau de décision."""
    etat.niveaux.append(len(etat.trail))


def annuler_niveau(etat: EtatSolveur) -> None:
    """Annule toutes les affectations du dernier niveau de décision."""
    debut = etat.niveaux.pop()
    for litteral in reversed(etat.trail[debut:]):
        etat.affectations[abs(litteral)] = -1
    del etat.trail[debut:]
    etat.prochain_a_propager = min(etat.prochain_a_propager, debut)
