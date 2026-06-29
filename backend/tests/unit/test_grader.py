from harness.eval.grader import calculate_grade


def test_grade_a() -> None:
    r = calculate_grade({"m1": 0.95, "m2": 0.92})
    assert r.letter == "A" and r.score == 93.5


def test_grade_b() -> None:
    assert calculate_grade({"m1": 0.85, "m2": 0.80}).letter == "B"


def test_grade_c() -> None:
    assert calculate_grade({"m1": 0.75, "m2": 0.72}).letter == "C"


def test_grade_d() -> None:
    assert calculate_grade({"m1": 0.65, "m2": 0.60}).letter == "D"


def test_grade_f() -> None:
    assert calculate_grade({"m1": 0.40, "m2": 0.50}).letter == "F"


def test_empty() -> None:
    r = calculate_grade({})
    assert r.letter == "F" and r.score == 0.0


def test_perfect() -> None:
    r = calculate_grade({"m1": 1.0, "m2": 1.0})
    assert r.letter == "A" and r.score == 100.0
