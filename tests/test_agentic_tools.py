"""Tests for tool validation, approvals, sandboxing, and the built-in tools."""

import asyncio
import sys

import pytest

from agentic.config import NetworkConfig
from agentic.llm.scripted import ScriptedProvider
from agentic.tools.base import Tool, ToolContext, ToolError, schema, truncate, validate_args
from agentic.tools.system import check_command
from agentic.tools.web import _DuckDuckGoParser, check_url, html_to_text


def call(runtime, name, args, origin="cli"):
    ctx = ToolContext(runtime, "run1", "tester", origin)
    return asyncio.run(
        runtime.tools.call(name, args, ctx, runtime.gate, timeout=30, output_limit=5_000)
    )


def test_file_tools_round_trip(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"write": "auto"})

    assert call(runtime, "write_file", {"path": "notes/a.txt", "content": "alpha\nbeta\n"}).ok
    read = call(runtime, "read_file", {"path": "notes/a.txt"})
    assert "    1  alpha" in read.content and "    2  beta" in read.content

    assert call(
        runtime, "edit_file", {"path": "notes/a.txt", "old_text": "beta", "new_text": "gamma"}
    ).ok
    assert (runtime.settings.workspace_path / "notes/a.txt").read_text() == "alpha\ngamma\n"

    found = call(runtime, "search_files", {"pattern": "gam+a"})
    assert "notes/a.txt:2: gamma" in found.content
    assert "notes/" in call(runtime, "list_dir", {}).content


def test_edit_requires_unique_match(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"write": "auto"})
    call(runtime, "write_file", {"path": "x.txt", "content": "a a"})
    result = call(runtime, "edit_file", {"path": "x.txt", "old_text": "a", "new_text": "b"})
    assert not result.ok and "appears 2 times" in result.content


@pytest.mark.parametrize("path", ["../escape.txt", "sub/../../escape.txt"])
def test_paths_cannot_escape_workspace(make_runtime, path) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"write": "auto"})
    result = call(runtime, "write_file", {"path": path, "content": "x"})
    assert not result.ok and "outside the workspace" in result.content
    assert not (runtime.settings.root / "escape.txt").exists()


def test_absolute_path_outside_workspace_is_refused(make_runtime, tmp_path) -> None:
    runtime = make_runtime(ScriptedProvider())
    result = call(runtime, "read_file", {"path": str(tmp_path / "elsewhere.txt")})
    assert not result.ok and "outside the workspace" in result.content


def test_ask_permission_is_denied_without_an_approver(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider())
    result = call(runtime, "write_file", {"path": "a.txt", "content": "x"})
    assert not result.ok and "no approver" in result.content
    assert not (runtime.settings.workspace_path / "a.txt").exists()


def test_approver_decides_and_deny_policy_wins(make_runtime) -> None:
    seen = []

    async def approver(request):
        seen.append(request.tool)
        return True

    runtime = make_runtime(ScriptedProvider(), approver=approver, permissions={"execute": "deny"})
    assert call(runtime, "write_file", {"path": "a.txt", "content": "x"}).ok
    assert seen == ["write_file"]
    denied = call(runtime, "run_python", {"code": "print(1)"})
    assert not denied.ok and "denied by policy" in denied.content
    assert seen == ["write_file"]


def test_scheduled_origin_only_gets_unattended_permissions(make_runtime) -> None:
    async def approver(request):
        raise AssertionError("scheduled runs must never prompt")

    runtime = make_runtime(ScriptedProvider(), approver=approver)
    result = call(runtime, "write_file", {"path": "a.txt", "content": "x"}, origin="schedule:abc")
    assert not result.ok and "unattended_permissions" in result.content
    assert call(runtime, "list_dir", {}, origin="schedule:abc").ok


def test_registry_reports_bad_calls_without_raising(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider())
    assert "Unknown tool" in call(runtime, "does_not_exist", {}).content
    assert "missing required argument 'path'" in call(runtime, "read_file", {}).content
    assert "unknown argument" in call(runtime, "list_dir", {"bogus": 1}).content


def test_tool_exceptions_and_timeouts_become_results(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider())

    def boom(args, ctx):
        raise RuntimeError("kaput")

    async def slow(args, ctx):
        await asyncio.sleep(5)

    runtime.tools.register(Tool("boom", "fails", schema({}), "read", boom))
    runtime.tools.register(
        Tool("slow", "sleeps", schema({}), "read", slow, blocking=False, timeout=0.05)
    )
    assert "RuntimeError: kaput" in call(runtime, "boom", {}).content
    assert "timed out" in call(runtime, "slow", {}).content


def test_validate_args_checks_types_enums_and_bounds() -> None:
    params = schema(
        {
            "n": {"type": "integer", "minimum": 1, "maximum": 5},
            "mode": {"type": "string", "enum": ["a", "b"]},
            "flag": {"type": "boolean"},
        },
        ["n"],
    )
    assert validate_args(params, {"n": 2.0}) == {"n": 2}
    for bad in ({"n": True}, {"n": 9}, {"n": 1, "mode": "c"}, {"n": "1"}, {"n": 1, "flag": 1}):
        with pytest.raises(ToolError):
            validate_args(params, bad)


def test_truncate_keeps_head_and_tail() -> None:
    text = "A" * 100 + "Z" * 100
    clipped = truncate(text, 40)
    assert clipped.startswith("A" * 30) and clipped.endswith("Z" * 10)
    assert "160 characters truncated" in clipped


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /",
        "sudo rm -rf ~",
        "format c:",
        "shutdown /s /t 0",
        "ls; reboot",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
        "Stop-Computer -Force",
    ],
)
def test_destructive_commands_are_blocked(command) -> None:
    with pytest.raises(ToolError):
        check_command(command)


@pytest.mark.parametrize("command", ["rm -rf build", "echo graceful shutdown", "git status"])
def test_ordinary_commands_pass_the_guard(command) -> None:
    check_command(command)


def test_run_python_executes_in_workspace(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"execute": "auto"})
    result = call(runtime, "run_python", {"code": "import os\nprint(6 * 7, os.getcwd())"})
    assert result.ok
    assert "42" in result.content and "exit code: 0" in result.content
    assert str(runtime.settings.workspace_path) in result.content


@pytest.mark.skipif(sys.platform != "win32", reason="uses PowerShell syntax")
def test_run_command_returns_exit_code(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"execute": "auto"})
    result = call(runtime, "run_command", {"command": "Write-Output hello; exit 3"})
    assert "exit code: 3" in result.content and "hello" in result.content


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000",
        "http://localhost/admin",
        "http://10.0.0.5",
        "http://[::1]/",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_check_url_refuses_local_and_non_http(url) -> None:
    with pytest.raises(ToolError):
        check_url(url, NetworkConfig())


def test_check_url_allowlist() -> None:
    network = NetworkConfig(allowed_domains=["example.com"], allow_private_hosts=True)
    assert check_url("https://docs.example.com/x", network)
    with pytest.raises(ToolError, match="allowed_domains"):
        check_url("https://example.org", network)


def test_html_to_text_drops_scripts_and_keeps_title() -> None:
    title, text = html_to_text(
        "<html><head><title>Hi there</title><script>evil()</script></head>"
        "<body><h1>Header</h1><p>First  para</p><style>.x{}</style><p>Second</p></body></html>"
    )
    assert title == "Hi there"
    assert text == "Header\nFirst para\nSecond"


def test_duckduckgo_parser_decodes_result_links() -> None:
    parser = _DuckDuckGoParser()
    parser.feed(
        '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa">'
        'Example <b>A</b></a><a class="result__snippet">Snippet text</a>'
    )
    assert parser.results == [
        {"title": "Example A", "url": "https://example.com/a", "snippet": "Snippet text"}
    ]


def test_run_python_redirects_shell_commands(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider(), overrides={"execute": "auto"})
    result = call(runtime, "run_python", {"code": "python stats.py"})
    assert not result.ok and "call run_command with: python stats.py" in result.content
