from src.agents.executor import Executor
from src.schemas import Plan, PlanStep
from src.tools.builtins import make_default_registry

from .conftest import ScriptedLLM, message, text_block, tool_use_block


def _plan():
    return Plan(goal="write a file", steps=[PlanStep(description="write hi.txt", rationale="needed")])


def test_executor_runs_tool_then_summarizes(tmp_path):
    registry = make_default_registry(tmp_path)
    llm = ScriptedLLM(
        create_responses=[
            # First turn: model calls write_file
            message(
                [tool_use_block("tu_1", "write_file", {"path": "hi.txt", "content": "hi"})],
                stop_reason="tool_use",
            ),
            # Second turn: model wraps up
            message([text_block("Done. Wrote hi.txt.")], stop_reason="end_turn"),
        ]
    )
    executor = Executor("executor", "sys", llm, registry)

    result = executor.execute("write a file", _plan())

    assert result == "Done. Wrote hi.txt."
    assert (tmp_path / "hi.txt").read_text() == "hi"
    # Two create calls: initial + after feeding back the tool result.
    assert len(llm.create_calls) == 2
    # The second call's messages must include the tool_result we fed back.
    second_msgs = llm.create_calls[1]["messages"]
    assert any(
        isinstance(m["content"], list)
        and any(b.get("type") == "tool_result" for b in m["content"] if isinstance(b, dict))
        for m in second_msgs
    )


def test_executor_includes_feedback(tmp_path):
    registry = make_default_registry(tmp_path)
    llm = ScriptedLLM(create_responses=[message([text_block("ok")], stop_reason="end_turn")])
    executor = Executor("executor", "sys", llm, registry)

    executor.execute("g", _plan(), feedback="fix the typo")
    task_text = llm.create_calls[0]["messages"][0]["content"]
    assert "fix the typo" in task_text


def test_executor_respects_iteration_cap(tmp_path):
    registry = make_default_registry(tmp_path)
    # Always asks for a tool; loop must stop at the cap instead of spinning forever.
    responses = [
        message([tool_use_block(f"tu_{i}", "list_dir", {"path": "."})], stop_reason="tool_use")
        for i in range(5)
    ]
    llm = ScriptedLLM(create_responses=responses)
    executor = Executor("executor", "sys", llm, registry, max_tool_iterations=3)

    executor.execute("g", _plan())
    assert len(llm.create_calls) == 3
