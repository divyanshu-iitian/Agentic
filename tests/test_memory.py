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
