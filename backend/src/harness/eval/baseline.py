from dataclasses import dataclass, field


@dataclass(frozen=True)
class BaselineSnapshot:
    scores: dict[str, float]
    thresholds: dict[str, float]
    tolerance: float = 0.05


@dataclass(frozen=True)
class Regression:
    metric_name: str
    baseline_score: float
    current_score: float
    threshold: float
    reason: str  # "below_floor" | "exceeded_tolerance"


@dataclass
class RegressionResult:
    regressions: list[Regression] = field(default_factory=list)
    deltas: dict[str, float] = field(default_factory=dict)

    @property
    def has_regression(self) -> bool:
        return len(self.regressions) > 0


def compare_to_baseline(
    current_scores: dict[str, float],
    baseline: BaselineSnapshot,
) -> RegressionResult:
    regressions: list[Regression] = []
    deltas: dict[str, float] = {}

    for metric_name, baseline_score in baseline.scores.items():
        if metric_name not in current_scores:
            continue

        current = current_scores[metric_name]
        delta = current - baseline_score
        deltas[metric_name] = delta

        threshold = baseline.thresholds.get(metric_name, 0.0)

        if current < threshold:
            regressions.append(Regression(
                metric_name=metric_name, baseline_score=baseline_score,
                current_score=current, threshold=threshold, reason="below_floor",
            ))
        elif delta < -baseline.tolerance:
            regressions.append(Regression(
                metric_name=metric_name, baseline_score=baseline_score,
                current_score=current, threshold=threshold, reason="exceeded_tolerance",
            ))

    return RegressionResult(regressions=regressions, deltas=deltas)
