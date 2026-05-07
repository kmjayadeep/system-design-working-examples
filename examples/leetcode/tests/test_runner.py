from app.runner import evaluate_python


def test_evaluate_python_accepts_solution():
    result = evaluate_python(
        "def solve(a, b):\n    return a + b",
        [{"input": "(2, 3)", "expected": "5"}],
    )

    assert result["status"] == "accepted"


def test_evaluate_python_blocks_imports():
    result = evaluate_python("import os\ndef solve():\n    return 1", [{"input": "()", "expected": "1"}])

    assert result["status"] == "runtime_error"
