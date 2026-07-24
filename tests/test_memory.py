"""Tests for feedback persistence and retrieval."""

from core import memory as memory_module


def test_feedback_round_trip(tmp_path, monkeypatch) -> None:
    memory_file = tmp_path / "memory.json"
    monkeypatch.setattr(memory_module, "MEMORY_FILE", memory_file)

    memory = memory_module.LongTermMemory()
    memory.save_feedback(
        task="open chrome",
        feedback="Use the browser action instead of raw clicks.",
        steps_taken=["open_app"],
    )

    reloaded = memory_module.LongTermMemory()
    prompt = reloaded.get_relevant_feedback("Please open chrome")

    assert "Use the browser action" in prompt
    assert reloaded.memories[0]["steps"] == ["open_app"]


def test_feedback_is_deduplicated_and_ranked(tmp_path, monkeypatch) -> None:
    memory_file = tmp_path / "memory.json"
    monkeypatch.setattr(memory_module, "MEMORY_FILE", memory_file)

    memory = memory_module.LongTermMemory()
    memory.save_feedback("open browser", "Prefer a semantic browser action.", ["open_app"])
    memory.save_feedback("open browser", "Prefer a semantic browser action.", ["open_app"])
    memory.save_feedback("write document", "Save before closing.", ["type"])

    prompt = memory.get_relevant_feedback("open the browser")

    assert len(memory.memories) == 2
    assert "semantic browser action" in prompt
    assert "Save before closing" not in prompt


def test_memory_retention_is_bounded(tmp_path, monkeypatch) -> None:
    memory_file = tmp_path / "memory.json"
    monkeypatch.setattr(memory_module, "MEMORY_FILE", memory_file)
    monkeypatch.setattr(memory_module, "MAX_MEMORIES", 3)

    memory = memory_module.LongTermMemory()
    for index in range(5):
        memory.save_feedback(f"task {index}", f"feedback {index}", [])

    assert [item["task"] for item in memory.memories] == ["task 2", "task 3", "task 4"]
    assert not memory_file.with_suffix(".json.tmp").exists()
