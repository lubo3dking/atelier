from src.agents.planner import Planner
from src.agents.reviewer import Reviewer
from src.schemas import Plan, PlanStep, ReviewVerdict

from .conftest import ScriptedLLM


def test_planner_passes_memory_context():
    plan = Plan(goal="g", steps=[PlanStep(description="s", rationale="r")])
    llm = ScriptedLLM(plan=plan)
    planner = Planner("planner", "sys", llm)

    out = planner.plan("build a thing", memory_context="prior run failed")

    assert out is plan
    assert llm.parse_calls[0]["schema"] is Plan
    user_msg = llm.parse_calls[0]["messages"][0]["content"]
    assert "build a thing" in user_msg
    assert "prior run failed" in user_msg


def test_reviewer_returns_verdict():
    verdict = ReviewVerdict(approved=False, score=30, feedback="missing tests")
    llm = ScriptedLLM(verdicts=[verdict])
    reviewer = Reviewer("reviewer", "sys", llm)
    plan = Plan(goal="g", steps=[PlanStep(description="s", rationale="r")])

    out = reviewer.review("g", plan, "the result")

    assert out is verdict
    assert llm.parse_calls[0]["schema"] is ReviewVerdict
    user_msg = llm.parse_calls[0]["messages"][0]["content"]
    assert "the result" in user_msg
