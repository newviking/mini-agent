from __future__ import annotations

import ast
import operator

from tools.base import BaseTool


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluate arithmetic expressions using numbers and operators."

    _binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }
    _unary_ops = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def run(self, args: dict, session: dict | None = None) -> dict:
        expression = args.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            return {"ok": False, "error": "expression is required"}

        try:
            tree = ast.parse(expression, mode="eval")
            result = self._eval(tree.body)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        return {"ok": True, "result": result}

    def _eval(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in self._binary_ops:
            left = self._eval(node.left)
            right = self._eval(node.right)
            return self._binary_ops[type(node.op)](left, right)

        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_ops:
            operand = self._eval(node.operand)
            return self._unary_ops[type(node.op)](operand)

        raise ValueError("Unsupported expression")

