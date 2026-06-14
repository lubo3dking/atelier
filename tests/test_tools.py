from src.tools.builtins import make_default_registry
from src.tools.registry import Tool, ToolRegistry


def test_register_and_definitions():
    reg = ToolRegistry()
    reg.register(Tool("echo", "echo back", {"type": "object", "properties": {}}, lambda a: "ok"))
    assert len(reg) == 1
    defs = reg.definitions()
    assert defs[0]["name"] == "echo"
    assert "input_schema" in defs[0]


def test_duplicate_registration_raises():
    reg = ToolRegistry()
    t = Tool("x", "d", {"type": "object", "properties": {}}, lambda a: "")
    reg.register(t)
    try:
        reg.register(t)
    except ValueError:
        return
    raise AssertionError("expected ValueError on duplicate registration")


def test_call_unknown_tool_returns_error():
    reg = ToolRegistry()
    assert reg.call("nope", {}).startswith("Error: unknown tool")


def test_call_handler_exception_is_caught():
    reg = ToolRegistry()

    def boom(args):
        raise RuntimeError("kaboom")

    reg.register(Tool("boom", "d", {"type": "object", "properties": {}}, boom))
    out = reg.call("boom", {})
    assert out.startswith("Error:") and "kaboom" in out


def test_write_then_read(tmp_path):
    reg = make_default_registry(tmp_path)
    assert "Wrote" in reg.call("write_file", {"path": "a.txt", "content": "hello"})
    assert reg.call("read_file", {"path": "a.txt"}) == "hello"


def test_list_dir(tmp_path):
    reg = make_default_registry(tmp_path)
    reg.call("write_file", {"path": "sub/b.txt", "content": "x"})
    listing = reg.call("list_dir", {"path": "."})
    assert "sub/" in listing


def test_read_missing_file(tmp_path):
    reg = make_default_registry(tmp_path)
    assert reg.call("read_file", {"path": "missing.txt"}).startswith("Error: no such file")


def test_path_traversal_blocked(tmp_path):
    reg = make_default_registry(tmp_path)
    out = reg.call("read_file", {"path": "../../etc/passwd"})
    assert out.startswith("Error:") and "escapes the workspace" in out
