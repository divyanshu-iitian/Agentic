"""Tests for the gateway API: auth, origin checks, runs, approvals, schedules, memory."""

import time

import pytest
from fastapi.testclient import TestClient

from agentic.gateway import create_app
from agentic.llm.scripted import ScriptedProvider, tool_reply


@pytest.fixture
def gateway(make_runtime, monkeypatch):
    def factory(provider=None, token=None):
        if token:
            monkeypatch.setenv("AGENTIC_TOKEN", token)
        else:
            monkeypatch.delenv("AGENTIC_TOKEN", raising=False)
        runtime = make_runtime(provider or ScriptedProvider())
        app = create_app(runtime.settings, runtime=runtime, background=False)
        return TestClient(app), runtime

    return factory


def wait_for(client, run_id, status="completed", timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] == status:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached {status}: {run}")


def test_status_and_dashboard(gateway) -> None:
    client, _ = gateway()
    with client:
        status = client.get("/api/status").json()
        assert status["heads"] >= 9 and status["tools"] >= 15 and status["auth"] is False
        assert "Agentic Mission Control" in client.get("/").text
        names = {h["name"] for h in client.get("/api/heads").json()}
        assert {"assistant", "planner", "researcher"} <= names
        tools = {t["name"]: t for t in client.get("/api/tools").json()}
        assert tools["write_file"]["policy"] == "ask"


def test_token_is_enforced(gateway) -> None:
    client, _ = gateway(token="s3cret")
    with client:
        assert client.get("/api/status").status_code == 401
        assert (
            client.get("/api/status", headers={"Authorization": "Bearer nope"}).status_code == 401
        )
        ok = client.get("/api/status", headers={"Authorization": "Bearer s3cret"})
        assert ok.status_code == 200 and ok.json()["auth"] is True
        assert client.get("/api/status?token=s3cret").status_code == 200
        assert client.get("/").status_code == 200  # the page itself asks for the token


def test_cross_origin_and_foreign_host_are_refused(gateway) -> None:
    client, _ = gateway()
    with client:
        evil = client.post(
            "/api/runs", json={"goal": "x"}, headers={"Origin": "https://evil.example"}
        )
        assert evil.status_code == 403
        rebinding = client.get("/api/status", headers={"Host": "attacker.example:8765"})
        assert rebinding.status_code == 403


def test_run_lifecycle(gateway) -> None:
    client, _ = gateway(ScriptedProvider(["All done."]))
    with client:
        run_id = client.post("/api/runs", json={"goal": "say done"}).json()["run_id"]
        run = wait_for(client, run_id)
        assert run["result"] == "All done."
        assert [e["type"] for e in run["events"]][0] == "run.start"
        assert client.get("/api/runs").json()[0]["id"] == run_id
        assert client.post("/api/runs", json={"goal": "x", "head": "nobody"}).status_code == 400


def test_approval_round_trip(gateway) -> None:
    provider = ScriptedProvider([tool_reply("write_file", path="ok.txt", content="yes"), "Saved."])
    client, runtime = gateway(provider)
    with client:
        run_id = client.post("/api/runs", json={"goal": "save a file"}).json()["run_id"]
        deadline = time.time() + 10
        pending = []
        while not pending and time.time() < deadline:
            pending = client.get("/api/approvals").json()
            time.sleep(0.05)
        assert pending and pending[0]["tool"] == "write_file"
        assert pending[0]["args"] == {"path": "ok.txt", "content": "yes"}

        decision = client.post(f"/api/approvals/{pending[0]['id']}", json={"approve": True})
        assert decision.status_code == 200
        run = wait_for(client, run_id)
        assert run["result"] == "Saved."
        assert (runtime.settings.workspace_path / "ok.txt").read_text() == "yes"
        types = [e["type"] for e in run["events"]]
        assert "approval.requested" in types and "approval.resolved" in types
        assert client.post("/api/approvals/missing", json={"approve": True}).status_code == 404


def test_schedules_and_memories(gateway) -> None:
    client, _ = gateway()
    with client:
        both = client.post(
            "/api/schedules", json={"goal": "g", "every_minutes": 5, "cron": "* * * * *"}
        )
        assert both.status_code == 400
        assert client.post("/api/schedules", json={"goal": "g", "cron": "nope"}).status_code == 400
        created = client.post("/api/schedules", json={"goal": "daily brief", "cron": "0 8 * * *"})
        assert created.status_code == 201
        schedules = client.get("/api/schedules").json()
        assert schedules[0]["cron"] == "0 8 * * *"
        assert client.delete(f"/api/schedules/{created.json()['id']}").json() == {"ok": True}

        memory_id = client.post("/api/memories", json={"text": "Standup is at 10am"}).json()["id"]
        assert client.get("/api/memories?q=standup").json()[0]["id"] == memory_id
        assert client.delete(f"/api/memories/{memory_id}").status_code == 200
        assert client.delete(f"/api/memories/{memory_id}").status_code == 404


def test_chat_endpoint(gateway) -> None:
    client, _ = gateway(ScriptedProvider(["Hello!"]))
    with client:
        assert client.post("/api/chat", json={"message": "hi"}).json() == {"reply": "Hello!"}
        reply = client.post("/api/chat", json={"message": "/remember the wifi is guest-5g"}).json()
        assert reply["reply"].startswith("Saved memory")
