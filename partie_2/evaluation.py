"""Independent evaluation of the propositional AST, mainly for validation."""

from collections.abc import Mapping

from syntax import And, Constraint, Implies, Not, Or, Program, Var


def evaluate_expression(expression: object, valuation: Mapping[str, bool]) -> bool:
    """Evaluate an expression under a complete source-level valuation."""
    if isinstance(expression, Var):
        return valuation[expression.name]
    if isinstance(expression, Not):
        return not evaluate_expression(expression.expr, valuation)
    if isinstance(expression, And):
        return evaluate_expression(expression.left, valuation) and evaluate_expression(
            expression.right, valuation
        )
    if isinstance(expression, Or):
        return evaluate_expression(expression.left, valuation) or evaluate_expression(
            expression.right, valuation
        )
    if isinstance(expression, Implies):
        return not evaluate_expression(
            expression.left, valuation
        ) or evaluate_expression(expression.right, valuation)
    raise TypeError(f"expression propositionnelle inattendue : {expression!r}")


def evaluate_program(program: Program, valuation: Mapping[str, bool]) -> bool:
    """Return whether every constraint in ``program`` is true."""
    return all(
        evaluate_expression(statement.expr, valuation)
        for statement in program.statements
        if isinstance(statement, Constraint)
    )
