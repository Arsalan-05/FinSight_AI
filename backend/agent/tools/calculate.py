"""Safe arithmetic tool — AST whitelist only, never Python eval()."""

from __future__ import annotations

import ast
import operator
from typing import Any, Union

Number = Union[int, float]

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    # Python 3.8+: Constant; Num kept for older AST dumps / whitelist completeness
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed")
        return node.value

    if isinstance(node, ast.Num):  # pragma: no cover - legacy AST node
        return node.n

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if op_type is ast.Div and right == 0:
            raise ZeroDivisionError("Division by zero")
        return _BIN_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _UNARY_OPS[op_type](_eval_node(node.operand))

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def calculate(expression: str) -> dict[str, Any]:
    """Evaluate a simple arithmetic expression safely.

    Allowed: numbers, +, -, *, /, parentheses, unary +/-.
    """
    text = (expression or "").strip()
    if not text:
        return {"error": "Empty expression"}

    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        return {"error": f"Invalid expression: {exc.msg}"}

    try:
        value = _eval_node(tree)
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except ValueError as exc:
        return {"error": str(exc)}

    if isinstance(value, float):
        # Normalize near-integers and money-friendly precision
        rounded = round(value, 10)
        if rounded == int(rounded):
            result: Number = int(rounded)
        else:
            result = rounded
    else:
        result = value

    return {"expression": text, "result": result}
