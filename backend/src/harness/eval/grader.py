from dataclasses import dataclass


@dataclass(frozen=True)
class GradeResult:
    letter: str
    score: float  # 0-100


def calculate_grade(metric_averages: dict[str, float]) -> GradeResult:
    if not metric_averages:
        return GradeResult(letter="F", score=0.0)
    mean = sum(metric_averages.values()) / len(metric_averages)
    score = round(mean * 100, 1)
    if score >= 90:
        letter = "A"
    elif score >= 80:
        letter = "B"
    elif score >= 70:
        letter = "C"
    elif score >= 60:
        letter = "D"
    else:
        letter = "F"
    return GradeResult(letter=letter, score=score)
