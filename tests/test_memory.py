from src.memory.store import MemoryStore


def test_empty_context(tmp_path):
    store = MemoryStore(tmp_path / "runs.json")
    assert "No prior runs" in store.context_for("anything")
    assert store.recent() == []


def test_add_and_recent(tmp_path):
    store = MemoryStore(tmp_path / "runs.json")
    store.add({"goal": "g1", "approved": True, "score": 90, "attempts": 1})
    store.add({"goal": "g2", "approved": False, "score": 40, "attempts": 3})
    recent = store.recent()
    assert len(recent) == 2
    assert recent[-1]["goal"] == "g2"
    assert "timestamp" in recent[0]


def test_recent_truncates(tmp_path):
    store = MemoryStore(tmp_path / "runs.json")
    for i in range(10):
        store.add({"goal": f"g{i}", "approved": True, "score": 100, "attempts": 1})
    assert len(store.recent(3)) == 3
    assert store.recent(3)[-1]["goal"] == "g9"


def test_context_digest(tmp_path):
    store = MemoryStore(tmp_path / "runs.json")
    store.add({"goal": "build x", "approved": True, "score": 95, "attempts": 1})
    ctx = store.context_for("build x")
    assert "build x" in ctx and "approved" in ctx


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "runs.json"
    path.write_text("{not json", encoding="utf-8")
    store = MemoryStore(path)
    assert store.recent() == []
