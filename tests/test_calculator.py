from tools.calculator import CalculatorTool


def test_calculator_evaluates_allowed_expression():
    tool = CalculatorTool()

    result = tool.run({"expression": "2 + 3 * (4 - 1) ** 2"})

    assert result == {"ok": True, "result": 29}


def test_calculator_rejects_function_calls():
    tool = CalculatorTool()

    result = tool.run({"expression": "__import__('os').system('echo unsafe')"})

    assert result["ok"] is False
    assert "Unsupported expression" in result["error"]


def test_calculator_rejects_missing_expression():
    tool = CalculatorTool()

    result = tool.run({})

    assert result["ok"] is False
    assert "expression" in result["error"]
