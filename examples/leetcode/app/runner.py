import ast


def evaluate_python(code: str, test_cases: list[dict]) -> dict:
    if "import " in code or "__" in code or "open(" in code:
        return {"status": "runtime_error", "passed": 0, "total": len(test_cases), "message": "blocked by sandbox policy"}
    namespace: dict = {}
    try:
        allowed_builtins = {
            "enumerate": enumerate,
            "len": len,
            "range": range,
            "sum": sum,
            "sorted": sorted,
        }
        exec(compile(code, "<submission>", "exec"), {"__builtins__": allowed_builtins}, namespace)
        solve = namespace.get("solve")
        if not callable(solve):
            return {"status": "runtime_error", "passed": 0, "total": len(test_cases), "message": "define solve(...) function"}
        passed = 0
        for case in test_cases:
            args = ast.literal_eval(case["input"])
            expected = ast.literal_eval(case["expected"])
            actual = solve(*args)
            if actual == expected:
                passed += 1
        return {
            "status": "accepted" if passed == len(test_cases) else "wrong_answer",
            "passed": passed,
            "total": len(test_cases),
            "message": "ok",
        }
    except Exception as exc:
        return {"status": "runtime_error", "passed": 0, "total": len(test_cases), "message": str(exc)}
