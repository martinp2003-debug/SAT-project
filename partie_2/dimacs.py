"""DIMACS serialization for compiled propositional models."""

from pathlib import Path

from compiler import CompilationResult


def to_dimacs(compilation: CompilationResult) -> str:
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


def write_dimacs(path: str | Path, compilation: CompilationResult) -> None:
    """Write ``compilation`` to ``path`` without creating missing parents."""
    Path(path).write_text(to_dimacs(compilation), encoding="utf-8")
