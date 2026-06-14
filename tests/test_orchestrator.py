from src.agents.executor import Executor
from src.agents.planner import Planner
from src.agents.reviewer import Reviewer
from src.memory.store import MemoryStore
from src.orchestrator import Orchestrator
from src.schemas import Plan, PlanStep, ReviewVerdict
from src.tools.builtins import make_default_registry

from .conftest import ScriptedLLM, message, text_block


def _build(tmp_path, llm, max_revisions=3):
    registry = make_default_registry(tmp_path / "ws")
    planner = Planner("planner", "p", llm)
    executor = Executor("executor", "e", llm, registry)
    reviewer = Reviewer("reviewer", "r", llm)
    memory = MemoryStore(tmp_path / "runs.json")
    return Orchestrator(planner, executor, reviewer, memory, max_revisions=max_revisions)


def test_approves_first_attempt(tmp_path):
    plan = Plan(goal="g", steps=[PlanStep(description="s", rationale="r")])
    llm = ScriptedLLM(
        plan=plan,
        create_responses=[message([text_block("did it")], stop_reason="end_turn")],
        verdicts=[ReviewVerdict(approved=True, score=100, feedback="great")],
    )
    orch = _build(tmp_path, llm)

    result = orch.run("g")

    assert result.attempts == 1
    assert result.verdict.approved is True
    assert result.result == "did it"
    # The run was recorded in memory.
    assert orch.memory.recent()[-1]["goal"] == "g"


def test_revision_loop_then_approval(tmp_path):
    plan = Plan(goal="g", steps=[PlanStep(description="s", rationale="r")])
    llm = ScriptedLLM(
        plan=plan,
        create_responses=[
            message([text_block("first try")], stop_reason="end_turn"),
            message([text_block("second try")], stop_reason="end_turn"),
        ],
        verdicts=[
            ReviewVerdict(approved=False, score=40, feedback="add error handling"),
            ReviewVerdict(approved=True, score=90, feedback="ok now"),
        ],
    )
    orch = _build(tmp_path, llm)

    result = orch.run("g")

    assert result.attempts == 2
    assert result.verdict.approved is True
    assert result.result == "second try"
    # The reviewer feedback from attempt 1 must have reached the executor on attempt 2.
    second_task = llm.create_calls[1]["messages"][0]["content"]
    assert "add error handling" in second_task


def test_stops_at_max_revisions(tmp_path):
    plan = Plan(goal="g", steps=[PlanStep(description="s", rationale="r")])
    llm = ScriptedLLM(
        plan=plan,
        create_responses=[message([text_block(f"try {i}")], stop_reason="end_turn") for i in range(2)],
        verdicts=[
            ReviewVerdict(approved=False, score=10, feedback="nope"),
            ReviewVerdict(approved=False, score=20, feedback="still nope"),
        ],
    )
    orch = _build(tmp_path, llm, max_revisions=2)

    result = orch.run("g")

    assert result.attempts == 2
    assert result.verdict.approved is False
    assert orch.memory.recent()[-1]["approved"] is False
