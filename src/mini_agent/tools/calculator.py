from __future__ import annotations

import ast
import operator
from typing import Any

from mini_agent.session import Session

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class CalculatorTool:
    name = "calculator"
    description = "计算数学表达式。仅支持加减乘除、整除、取余、幂运算和括号。"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "要计算的表达式，例如 (2+3)*4"},
        },
        "required": ["expression"],
    }

    def execute(self, arguments: dict[str, Any], session: Session) -> str:
        expression = str(arguments.get("expression") or "").strip()
        if not expression:
            raise ValueError("缺少 expression")
        value = _safe_eval(expression)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(value)


def _safe_eval(expression: str) -> int | float:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"无效表达式: {expression}") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    raise ValueError(f"不安全或不受支持的表达式片段: {type(node).__name__}")
