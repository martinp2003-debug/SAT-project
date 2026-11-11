"""Semantic validation and Tseitin encoding of propositional programs."""

from dataclasses import dataclass

from syntax import And, Constraint, Implies, Not, Or, Program, Var, VarDecl


class CompilationError(ValueError):
    """An expected error in a source model."""


@dataclass
class CompilationResult:
    """A CNF formula and the stable mapping of source variables to DIMACS ids."""

    variable_count: int
    clauses: list[list[int]]
    name_to_id: dict[str, int]
    id_to_name: dict[int, str]


class _TseitinEncoder:
    def __init__(self, name_to_id: dict[str, int]):
        self.name_to_id = name_to_id
        self.next_id = len(name_to_id) + 1
        self.clauses: list[list[int]] = []

    def fresh_variable(self) -> int:
        variable = self.next_id
        self.next_id += 1
        return variable

    def encode(self, expression: object) -> int:
        """Return a literal equivalent to ``expression`` and append its clauses."""
        if isinstance(expression, Var):
            try:
                return self.name_to_id[expression.name]
            except KeyError as error:
                raise CompilationError(
                    f"variable non déclarée : {expression.name}"
                ) from error

        if isinstance(expression, Not):
            return -self.encode(expression.expr)

        if isinstance(expression, And):
            left = self.encode(expression.left)
            right = self.encode(expression.right)
            result = self.fresh_variable()
            # result <-> (left and right)
            self.clauses.extend(
                [[-result, left], [-result, right], [result, -left, -right]]
            )
            return result

        if isinstance(expression, Or):
            left = self.encode(expression.left)
            right = self.encode(expression.right)
            result = self.fresh_variable()
            # result <-> (left or right)
            self.clauses.extend(
                [[result, -left], [result, -right], [-result, left, right]]
            )
            return result

        if isinstance(expression, Implies):
            left = self.encode(expression.left)
            right = self.encode(expression.right)
            result = self.fresh_variable()
            # result <-> ((not left) or right)
            self.clauses.extend(
                [[result, left], [result, -right], [-result, -left, right]]
            )
            return result

        raise TypeError(f"expression propositionnelle inattendue : {expression!r}")


def compile_program(program: Program) -> CompilationResult:
    """Validate names and compile all constraints of ``program`` to CNF."""
    name_to_id: dict[str, int] = {}
    for statement in program.statements:
        if isinstance(statement, VarDecl):
            if statement.name in name_to_id:
                raise CompilationError(f"déclaration en double : {statement.name}")
            name_to_id[statement.name] = len(name_to_id) + 1

    encoder = _TseitinEncoder(name_to_id)
    for statement in program.statements:
        if isinstance(statement, Constraint):
            root = encoder.encode(statement.expr)
            encoder.clauses.append([root])
        elif not isinstance(statement, VarDecl):
            raise TypeError(f"instruction inattendue : {statement!r}")

    id_to_name = {identifier: name for name, identifier in name_to_id.items()}
    return CompilationResult(
        variable_count=encoder.next_id - 1,
        clauses=encoder.clauses,
        name_to_id=name_to_id,
        id_to_name=id_to_name,
    )
