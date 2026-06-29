from dataclasses import dataclass


@dataclass(frozen=True)
class GradeResult:
    letter: str
    score: float


_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (0.9, "A"),
    (0.8, "B"),
    (0.7, "C"),
    (0.6, "D"),
]


def calculate_grade(metric_averages: dict[str, float]) -> GradeResult:
    """Compute an overall letter grade from a dict of metric average scores."""
    if not metric_averages:
        return GradeResult(letter="F", score=0.0)

    overall = sum(metric_averages.values()) / len(metric_averages)

    for threshold, letter in _GRADE_THRESHOLDS:
        if overall >= threshold:
            return GradeResult(letter=letter, score=round(overall, 4))

    return GradeResult(letter="F", score=round(overall, 4))
