"""Tests for the head reasoning loop, delegation, chat, and prompt-mode tools."""

import asyncio

from agentic.llm.base import Message
from agentic.llm.providers import PromptToolProvider
from agentic.llm.scripted import ScriptedProvider, tool_reply


def events_of(runtime, run_id):
    return [row["type"] for row in runtime.store.events(run_id)]


def test_head_calls_tools_then_answers(make_runtime) -> None:
    provider = ScriptedProvider(
        [tool_reply("write_file", path="hello.txt", content="hi"), "Wrote hello.txt"]
    )
    runtime = make_runtime(provider, overrides={"write": "auto"})

    outcome = asyncio.run(runtime.run("create hello.txt"))

    assert outcome.ok and outcome.output == "Wrote hello.txt"
    assert (runtime.settings.workspace_path / "hello.txt").read_text() == "hi"
    types = events_of(runtime, outcome.run_id)
    assert types[:3] == ["run.start", "head.start", "tool.call"]
    assert types[-2:] == ["head.finish", "run.finish"]
    tool_message = provider.calls[1][-1]
    assert tool_message.role == "tool" and "Wrote 2 characters" in tool_message.content
    assert runtime.store.get_run(outcome.run_id)["status"] == "completed"


def test_declined_approval_is_reported_to_the_model(make_runtime) -> None:
    async def approver(request):
        return False

    provider = ScriptedProvider([tool_reply("run_python", code="print(1)"), "Could not run it."])
    runtime = make_runtime(provider, approver=approver)
    outcome = asyncio.run(runtime.run("run code"))

    assert outcome.output == "Could not run it."
    assert "declined" in provider.calls[1][-1].content


def test_identical_tool_calls_are_cut_off(make_runtime) -> None:
    replies = [tool_reply("list_dir")] * 5 + ["gave up"]
    runtime = make_runtime(ScriptedProvider(replies))
    outcome = asyncio.run(runtime.run("loop forever"))
    results = [
        row["data"]["output"]
        for row in runtime.store.events(outcome.run_id)
        if row["type"] == "tool.result"
    ]
    assert len(results) == 5
    assert all("Skipped" not in text for text in results[:3])
    assert all("Skipped: identical list_dir" in text for text in results[3:])


def test_step_budget_forces_a_final_answer(make_runtime) -> None:
    replies = [tool_reply("list_dir", path=str(i)) for i in range(3)] + ["partial summary"]
    provider = ScriptedProvider(replies)
    runtime = make_runtime(provider, limits={"max_steps": 3})
    outcome = asyncio.run(runtime.run("big job"))

    assert not outcome.ok and outcome.output == "partial summary"
    assert "step budget" in provider.calls[-1][-1].content


def test_unlisted_tools_are_not_offered_or_callable(make_runtime, tmp_path) -> None:
    heads = tmp_path / "heads"
    heads.mkdir()
    (heads / "reader.md").write_text(
        "---\nname: reader\ndescription: reads\ntools: [read_file]\n---\nRead only.\n",
        encoding="utf-8",
    )
    offered = []

    def responder(messages, tools):
        offered.append([tool.name for tool in tools or []])
        if len(offered) == 1:
            return tool_reply("write_file", path="x", content="y")
        return "done"

    runtime = make_runtime(ScriptedProvider(responder=responder), overrides={"write": "auto"})
    outcome = asyncio.run(runtime.run("try writing", head="reader"))

    assert offered[0] == ["read_file"]
    assert not (runtime.settings.workspace_path / "x").exists()
    result = [r for r in runtime.store.events(outcome.run_id) if r["type"] == "tool.result"][0]
    assert "Unknown tool 'write_file'" in result["data"]["output"]


def test_delegation_runs_another_head(make_runtime) -> None:
    def responder(messages, tools):
        system = messages[0].content
        last = messages[-1]
        if system.startswith("You are the Researcher head"):
            return "Paris is the capital of France."
        if last.role == "tool":
            return f"Answer: {last.content}"
        return tool_reply("delegate", head="researcher", task="capital of France?")

    runtime = make_runtime(ScriptedProvider(responder=responder))
    outcome = asyncio.run(runtime.run("Ask the researcher"))

    assert outcome.output == "Answer: [researcher completed]\nParis is the capital of France."
    starts = [r["agent"] for r in runtime.store.events(outcome.run_id) if r["type"] == "head.start"]
    assert starts == ["assistant", "researcher"]


def test_delegate_is_withheld_at_max_depth(make_runtime) -> None:
    offered = []

    def responder(messages, tools):
        offered.append({tool.name for tool in tools or []})
        return "ok"

    runtime = make_runtime(
        ScriptedProvider(responder=responder), limits={"max_delegation_depth": 0}
    )
    asyncio.run(runtime.run("anything"))
    assert "delegate" not in offered[0] and "read_file" in offered[0]


def test_memories_and_skills_reach_the_system_prompt(make_runtime, tmp_path) -> None:
    skill = tmp_path / "skills" / "deploy"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: deploy\ndescription: Deploy safely.\ntriggers:\n  - deploy\n---\n"
        "Always run tests before deploying.\n",
        encoding="utf-8",
    )
    provider = ScriptedProvider(["ok"])
    runtime = make_runtime(provider)
    runtime.store.add_memory("The production server is called atlas.")
    asyncio.run(runtime.run("deploy to the production server"))

    system = provider.calls[0][0].content
    assert "Always run tests before deploying." in system
    assert "The production server is called atlas." in system
    assert "untrusted data" in system


def test_chat_keeps_history_and_handles_commands(make_runtime) -> None:
    provider = ScriptedProvider(["Nice to meet you, Ada.", "Your name is Ada."])
    runtime = make_runtime(provider)

    assert asyncio.run(runtime.chat("s1", "My name is Ada")) == "Nice to meet you, Ada."
    asyncio.run(runtime.chat("s1", "What is my name?"))
    second_call = provider.calls[1]
    assert [m.content for m in second_call[1:3]] == ["My name is Ada", "Nice to meet you, Ada."]

    assert "Saved memory" in asyncio.run(runtime.chat("s1", "/remember likes tea"))
    assert "likes tea" in asyncio.run(runtime.chat("s1", "/memories"))
    assert asyncio.run(runtime.chat("s1", "/reset")) == "Conversation cleared."
    assert runtime.store.chat_history("s1") == []
    assert "Unknown command" in asyncio.run(runtime.chat("s1", "/nope"))


def test_prompt_tool_provider_parses_json_tool_calls() -> None:
    inner = ScriptedProvider(['Sure!\n```json\n{"tool": "list_dir", "args": {"path": "."}}\n```'])
    provider = PromptToolProvider(inner)
    from agentic.llm.base import ToolSpec

    spec = ToolSpec("list_dir", "List files", {"type": "object", "properties": {}})
    completion = provider.complete(
        [
            Message("system", "base"),
            Message("user", "go"),
            Message("tool", "file.txt", tool_call_id="1", name="list_dir"),
        ],
        [spec],
    )

    call = completion.message.tool_calls[0]
    assert (call.name, call.arguments) == ("list_dir", {"path": "."})
    sent = inner.calls[0]
    assert "TOOLS" in sent[0].content and '"tool": "<name>"' in sent[0].content
    assert sent[-1].role == "user" and sent[-1].content.startswith("TOOL RESULT (list_dir)")


def test_prompt_tool_provider_passes_plain_answers_through() -> None:
    provider = PromptToolProvider(ScriptedProvider(['The answer is {"tool": "unknown"}']))
    from agentic.llm.base import ToolSpec

    completion = provider.complete(
        [Message("user", "hi")], [ToolSpec("list_dir", "List", {"type": "object"})]
    )
    assert not completion.message.tool_calls


def test_empty_final_answer_gets_one_nudge(make_runtime) -> None:
    provider = ScriptedProvider([tool_reply("list_dir"), "", "Here is the answer."])
    runtime = make_runtime(provider)
    outcome = asyncio.run(runtime.run("list things"))
    assert outcome.ok and outcome.output == "Here is the answer."
    assert "Your last reply was empty" in provider.calls[2][-1].content

    stubborn = make_runtime(ScriptedProvider(["", ""]))
    outcome = asyncio.run(stubborn.run("say nothing"))
    assert not outcome.ok and outcome.output == "(the model returned an empty answer)"
