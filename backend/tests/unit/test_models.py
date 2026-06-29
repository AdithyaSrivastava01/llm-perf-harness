import uuid

from harness.db.models import Agent, Baseline, EvalRun
from harness.db.models import TestCase as TestCaseModel
from harness.db.models import User


def test_user_model_fields() -> None:
    user = User(email="test@example.com", name="Test", auth_provider="github")
    assert user.email == "test@example.com"
    assert user.auth_provider == "github"
    assert user.avatar_url is None


def test_agent_model_with_config() -> None:
    agent = Agent(
        name="weather-agent",
        adapter_type="tool_calling",
        config={"model": "gemini-2.5-flash", "tools": ["get_weather"]},
        capabilities=["text", "tools"],
        is_demo=True,
    )
    assert agent.name == "weather-agent"
    assert agent.config["model"] == "gemini-2.5-flash"
    assert "tools" in agent.capabilities


def test_eval_run_fields() -> None:
    run = EvalRun(
        suite_id=uuid.uuid4(),
        triggered_by=uuid.uuid4(),
        status="pending",
        is_baseline=False,
    )
    assert run.status == "pending"
    assert run.is_baseline is False


def test_test_case_fields() -> None:
    tc = TestCaseModel(
        suite_id=uuid.uuid4(),
        input={"turns": [{"role": "user", "content": "hello"}]},
        approved=False,
    )
    assert tc.approved is False
    assert tc.expected_output is None


def test_baseline_fields() -> None:
    baseline = Baseline(
        agent_id=uuid.uuid4(),
        suite_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        scores={"tool_trajectory_avg_score": 1.0},
        promoted_by=uuid.uuid4(),
        active=True,
    )
    assert baseline.active is True
    assert baseline.scores["tool_trajectory_avg_score"] == 1.0
