"""DIMACS serialization of a compiled model.

The compilation is any object with variable_count, clauses and id_to_name
(the names of the named SAT variables, written as "c var <id> <name>").
"""

from pathlib import Path


def to_dimacs(compilation) -> str:
    """Serialize a compilation result, including source-variable comments."""
    lines = [
        f"c var {identifier} {compilation.id_to_name[identifier]}"
        for identifier in sorted(compilation.id_to_name)
    ]
    lines.append(
        f"p cnf {compilation.variable_count} {len(compilation.clauses)}"
    )
    lines.extend(
        " ".join(map(str, clause)) + " 0" for clause in compilation.clauses
    )
    return "\n".join(lines) + "\n"


def write_dimacs(path: str | Path, compilation) -> None:
    """Write ``compilation`` to ``path`` without creating missing parents."""
    Path(path).write_text(to_dimacs(compilation), encoding="utf-8")
