"""Command line interface: `agentic <command>`."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from agentic import __version__
from agentic.approvals import ApprovalRequest
from agentic.config import CONFIG_FILENAME, Settings, load_settings
from agentic.events import Event

TEMPLATE = Path(__file__).resolve().parent / "templates" / "agentic.yaml"
PERMISSIONS = ("read", "memory", "network", "write", "execute", "schedule", "desktop")


class Style:
    enabled = sys.stdout.isatty() and not os.getenv("NO_COLOR")

    @classmethod
    def paint(cls, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if cls.enabled else text


def dim(text: str) -> str:
    return Style.paint("2", text)


def bold(text: str) -> str:
    return Style.paint("1", text)


def color(name: str, text: str) -> str:
    codes = {
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
    }
    return Style.paint(codes[name], text)


def one_line(value, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class EventPrinter:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def __call__(self, event: Event) -> None:
        d = event.data
        who = color("cyan", f"[{event.agent}]") + " " if event.agent else ""
        kind = event.type
        if kind == "swarm.plan":
            print(bold(f"\n▸ Plan ({len(d['tasks'])} tasks)"))
            for task in d["tasks"]:
                after = f" after {', '.join(task['depends_on'])}" if task["depends_on"] else ""
                print(
                    f"  {task['id']} → {color('cyan', task['head'])}{dim(after)}: "
                    f"{one_line(task['task'], 120)}"
                )
        elif kind == "task.start":
            label = "revising" if d.get("revision") else "starting"
            print(f"{who}{color('blue', label)} {d['task_id']}")
        elif kind == "task.finish":
            mark = color("green", "✓") if d["ok"] else color("red", "✗")
            print(f"{who}{mark} {d['task_id']} {dim(one_line(d['output'], 140))}")
        elif kind == "tool.call":
            print(f"{who}{color('magenta', '→ ' + d['tool'])} {dim(one_line(d['args'], 140))}")
        elif kind == "tool.result":
            mark = color("green", "ok") if d["ok"] else color("red", "error")
            detail = d["output"] if self.verbose else one_line(d["output"], 140)
            print(f"{who}  ← {mark} {dim(detail)}")
        elif kind == "head.thought" and self.verbose:
            print(f"{who}{dim(one_line(d['text'], 300))}")
        elif kind == "head.error":
            print(f"{who}{color('red', 'model error:')} {d['error']}")
        elif kind == "critic.verdict":
            if d["approved"]:
                print(f"{who}{color('green', 'approved')} {dim(one_line(d['feedback'], 140))}")
            else:
                print(
                    f"{who}{color('yellow', 'requested changes to ' + ', '.join(d['redo']))} "
                    f"{dim(one_line(d['feedback'], 140))}"
                )
        elif kind == "swarm.plan_invalid":
            print(f"{who}{color('yellow', 'plan rejected:')} {d['error']}")
        elif kind == "head.start" and self.verbose:
            print(f"{who}{dim('using ' + d['model'])}")


def make_cli_approver(auto_deny: bool = False):
    lock = asyncio.Lock()

    async def approve(request: ApprovalRequest) -> bool:
        if auto_deny or not sys.stdin.isatty():
            return False
        async with lock:  # parallel heads must not interleave prompts
            print()
            print(color("yellow", "⚠ Approval needed: ") + request.summary(1200))
            answer = await asyncio.to_thread(input, "  Allow? [y]es / [n]o / [a]lways this run: ")
            answer = answer.strip().casefold()
            if answer in {"a", "always"}:
                runtime_gate = approve.gate
                if runtime_gate is not None:
                    runtime_gate.grant_for_run(request.run_id, request.tool)
                return True
            return answer in {"y", "yes"}

    approve.gate = None
    return approve


def _settings(args) -> Settings:
    settings = load_settings(args.config)
    if getattr(args, "provider", None):
        settings.provider(args.provider)  # validates the name
        settings.default_provider = args.provider
    if getattr(args, "model", None):
        settings.provider().model = args.model
    if getattr(args, "workspace", None):
        settings.workspace = str(Path(args.workspace).resolve())
    return settings


def _overrides(args, settings: Settings) -> dict[str, str]:
    overrides: dict[str, str] = {}
    allowed = set()
    for item in getattr(args, "allow", None) or []:
        allowed.update(p.strip() for p in item.split(",") if p.strip())
    unknown = allowed - set(PERMISSIONS)
    if unknown:
        raise SystemExit(f"Unknown permission(s): {', '.join(sorted(unknown))}")
    if getattr(args, "yes", False):
        allowed.update(p for p in PERMISSIONS if getattr(settings.permissions, p) == "ask")
    for permission in allowed:
        overrides[permission] = "auto"
    return overrides


def _runtime(args, interactive: bool = True):
    from agentic.runtime import Runtime

    settings = _settings(args)
    approver = make_cli_approver(auto_deny=not interactive)
    runtime = Runtime(settings, approver=approver, permission_overrides=_overrides(args, settings))
    approver.gate = runtime.gate
    runtime.bus.subscribe(EventPrinter(verbose=getattr(args, "verbose", False)))
    return runtime


async def _with_mcp(runtime, coro_factory):
    await runtime.start_mcp()
    for name, error in runtime.mcp_errors.items():
        print(color("yellow", f"MCP server {name} unavailable: {error}"))
    try:
        return await coro_factory()
    finally:
        runtime.close()


def cmd_run(args, mode: str) -> int:
    runtime = _runtime(args)
    goal = " ".join(args.goal).strip()
    if not goal:
        raise SystemExit("Provide a goal.")
    label = "Swarm" if mode == "swarm" else f"Head '{args.head}'"
    provider = runtime.settings.provider()
    print(
        bold(f"{label} · {runtime.settings.default_provider}:{provider.model}")
        + dim(f" · workspace {runtime.settings.workspace_path}")
    )
    started = time.perf_counter()
    outcome = asyncio.run(
        _with_mcp(
            runtime,
            lambda: runtime.run(
                goal,
                mode=mode,
                head=getattr(args, "head", "assistant"),
                critic=not getattr(args, "no_critic", False),
            ),
        )
    )
    elapsed = time.perf_counter() - started
    status = color("green", "completed") if outcome.ok else color("red", "incomplete")
    print(f"\n{bold('Result')} {dim(f'({status}, {elapsed:.1f}s, run {outcome.run_id})')}\n")
    print(outcome.output)
    return 0 if outcome.ok else 1


def cmd_chat(args) -> int:
    runtime = _runtime(args)
    session = f"cli:{args.session}"
    settings = runtime.settings
    print(bold(f"Agentic chat · {settings.default_provider}:{settings.provider().model}"))
    print(dim("Type /help for commands, /swarm <goal> for the multi-head team, Ctrl+C to exit."))

    async def loop():
        while True:
            try:
                text = await asyncio.to_thread(input, color("green", "\nyou › "))
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not text.strip():
                continue
            if text.strip() in {"/exit", "/quit"}:
                return 0
            reply = await runtime.chat(session, text)
            print(f"\n{color('cyan', 'agentic ›')} {reply}")

    try:
        return asyncio.run(_with_mcp(runtime, loop))
    except KeyboardInterrupt:
        return 0


def cmd_serve(args) -> int:
    from agentic.gateway import serve

    settings = _settings(args)
    host = args.host or settings.gateway.host
    port = args.port or settings.gateway.port
    print(bold(f"Agentic gateway on http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"))
    serve(settings, host=host, port=port)
    return 0


def cmd_init(args) -> int:
    target = Path(args.config or CONFIG_FILENAME)
    if target.exists() and not args.force:
        print(f"{target} already exists (use --force to overwrite).")
    else:
        shutil.copyfile(TEMPLATE, target)
        print(color("green", f"Wrote {target}"))
    settings = load_settings(target)
    settings.workspace_path.mkdir(parents=True, exist_ok=True)
    settings.resolve(settings.heads_dir).mkdir(parents=True, exist_ok=True)
    print(f"Workspace: {settings.workspace_path}")
    print("Next: run `agentic doctor`, then `agentic chat`.")
    return 0


def cmd_doctor(args) -> int:
    import requests

    settings = _settings(args)
    problems = 0

    def report(ok: bool | None, label: str, detail: str = "") -> None:
        nonlocal problems
        mark = {True: color("green", "✓"), False: color("red", "✗"), None: color("yellow", "•")}[ok]
        problems += ok is False
        print(f" {mark} {label}" + (dim(f"  {detail}") if detail else ""))

    print(bold(f"Agentic {__version__} doctor"))
    report(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}")
    config_path = Path(args.config or CONFIG_FILENAME)
    report(
        True if config_path.exists() else None,
        "Config",
        str(config_path.resolve()) if config_path.exists() else "none; using defaults",
    )

    for name, provider in settings.providers.items():
        label = f"Provider {name} ({provider.type}:{provider.model})"
        if provider.type == "ollama":
            base = (provider.base_url or "http://127.0.0.1:11434").rstrip("/")
            try:
                models = [
                    m["name"]
                    for m in requests.get(f"{base}/api/tags", timeout=3).json().get("models", [])
                ]
            except requests.RequestException:
                report(False, label, f"Ollama not reachable at {base}; run `ollama serve`")
                continue
            pulled = provider.model in models or f"{provider.model}:latest" in models
            report(pulled, label, "ready" if pulled else f"run `ollama pull {provider.model}`")
        else:
            has_key = bool(provider.api_key()) or not provider.api_key_env
            report(
                has_key if name == settings.default_provider else (has_key or None),
                label,
                "key found" if has_key else f"set {provider.api_key_env}",
            )

    try:
        settings.workspace_path.mkdir(parents=True, exist_ok=True)
        probe = settings.workspace_path / ".write-test"
        probe.write_text("ok")
        probe.unlink()
        report(True, "Workspace", str(settings.workspace_path))
    except OSError as exc:
        report(False, "Workspace", str(exc))

    optional = {
        "playwright": "browser_render (pip install playwright && playwright install chromium)",
        "pyautogui": "desktop_* tools (pip install pyautogui)",
        "pytesseract": "desktop_read_screen (pip install pytesseract + Tesseract binary)",
    }
    for module, purpose in optional.items():
        report(True if importlib.util.find_spec(module) else None, f"Optional: {module}", purpose)
    if importlib.util.find_spec("pytesseract"):
        report(
            True if shutil.which("tesseract") else None,
            "Optional: tesseract binary",
            "found" if shutil.which("tesseract") else "not on PATH",
        )

    if settings.mcp_servers:
        from agentic.tools.mcp import MCPClient, mcp_tools

        for name, server in settings.mcp_servers.items():
            client = MCPClient(name, server, timeout=20)
            try:
                client.start()
                report(True, f"MCP {name}", f"{len(mcp_tools(client))} tools")
            except Exception as exc:
                report(False, f"MCP {name}", str(exc))
            finally:
                client.close()

    telegram = settings.channels.telegram
    if telegram.enabled:
        report(bool(os.getenv(telegram.token_env)), "Telegram token", telegram.token_env)
        report(
            bool(telegram.allowed_chat_ids) or None,
            "Telegram allowed chats",
            str(telegram.allowed_chat_ids or "none yet; message the bot and check the log"),
        )

    print(
        color("green", "\nAll required checks passed.")
        if not problems
        else color("red", f"\n{problems} problem(s) found.")
    )
    return 1 if problems else 0


def cmd_heads(args) -> int:
    from agentic.heads import load_heads

    settings = _settings(args)
    for head in load_heads(settings.resolve(settings.heads_dir)).values():
        source = "custom" if head.path and "profiles" not in head.path.parts else "built-in"
        tools = ", ".join(head.tools) or "no tools"
        print(f"{bold(head.name):<24} {head.description}")
        print(
            dim(f"    {source} · provider {head.provider or settings.default_provider} · {tools}")
        )
    return 0


def cmd_tools(args) -> int:
    runtime = _runtime(args, interactive=False)

    async def show():
        for tool in runtime.tools.all():
            policy = runtime.gate.mode_for(tool.permission)
            tint = {"auto": "green", "ask": "yellow", "deny": "red"}[policy]
            print(
                f"{bold(tool.name):<32} {color(tint, f'{tool.permission}:{policy}'):<26} "
                f"{one_line(tool.description, 90)}"
            )

    asyncio.run(_with_mcp(runtime, show))
    return 0


def cmd_runs(args) -> int:
    from agentic.store import Store

    settings = _settings(args)
    store = Store(settings.data_path / "agentic.db")
    if args.run_id:
        run = store.get_run(args.run_id)
        if not run:
            raise SystemExit("Run not found")
        print(bold(run["goal"]))
        print(dim(f"{run['mode']} · {run['status']} · {run['origin']}"))
        printer = EventPrinter(verbose=True)
        for row in store.events(args.run_id):
            printer(Event(row["type"], row["run_id"], row["agent"], row["data"], row["ts"]))
        print(f"\n{run['result'] or ''}")
        return 0
    for run in store.list_runs(args.limit):
        when = datetime.fromtimestamp(run["created_at"]).strftime("%Y-%m-%d %H:%M")
        tint = {"completed": "green", "running": "yellow"}.get(run["status"], "red")
        print(
            f"{run['id']}  {when}  {color(tint, run['status']):<20} {run['mode']:<6} "
            f"{one_line(run['goal'], 80)}"
        )
    return 0


def cmd_schedule(args) -> int:
    from agentic.cron import CronSchedule
    from agentic.store import Store
    from agentic.tools.core import next_run_time

    settings = _settings(args)
    store = Store(settings.data_path / "agentic.db")
    if args.action == "add":
        goal = " ".join(args.goal).strip()
        if bool(args.every) == bool(args.cron) or not goal:
            raise SystemExit("Provide a goal and exactly one of --every MINUTES or --cron EXPR")
        if args.cron:
            CronSchedule.parse(args.cron)
        interval = args.every * 60 if args.every else None
        schedule_id = store.add_schedule(
            name=args.name or goal[:60],
            goal=goal,
            mode="swarm" if args.swarm else "agent",
            head=args.head,
            interval_seconds=interval,
            cron=args.cron,
            notify=args.notify,
            next_run=next_run_time(interval, args.cron, time.time()),
        )
        print(
            color("green", f"Scheduled {schedule_id}.")
            + " Schedules run while `agentic serve` is running."
        )
    elif args.action == "remove":
        print("Removed." if store.delete_schedule(args.id) else "No such schedule.")
    else:
        rows = store.list_schedules()
        if not rows:
            print("No schedules.")
        for row in rows:
            when = (
                f"every {row['interval_seconds'] // 60}m"
                if row["interval_seconds"]
                else row["cron"]
            )
            nxt = datetime.fromtimestamp(row["next_run"]).strftime("%Y-%m-%d %H:%M")
            print(
                f"{row['id']}  {when:<16} next {nxt}  {row['mode']:<6} {one_line(row['goal'], 70)}"
            )
    return 0


def cmd_memory(args) -> int:
    from agentic.store import Store

    settings = _settings(args)
    store = Store(settings.data_path / "agentic.db")
    if args.action == "add":
        print(f"Saved #{store.add_memory(' '.join(args.text))}")
    elif args.action == "search":
        for row in store.search_memories(" ".join(args.text), 10):
            print(f"#{row['id']}: {row['text']}")
    elif args.action == "delete":
        print("Deleted." if store.delete_memory(int(args.text[0])) else "No such memory.")
    else:
        for row in store.list_memories(50):
            print(f"#{row['id']}: {row['text']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic", description="Local-first multi-head agent runtime."
    )
    parser.add_argument("--version", action="version", version=f"agentic {__version__}")
    parser.add_argument("-c", "--config", help=f"config file (default ./{CONFIG_FILENAME})")
    sub = parser.add_subparsers(dest="command", required=True)

    def runtime_flags(p):
        p.add_argument("--provider", help="provider name from the config")
        p.add_argument("--model", help="override the default provider's model")
        p.add_argument("--workspace", help="override the workspace directory")
        p.add_argument(
            "--allow", action="append", help="auto-approve permissions, e.g. --allow write,execute"
        )
        p.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="auto-approve every permission set to 'ask' (use with care)",
        )
        p.add_argument("-v", "--verbose", action="store_true", help="show full tool output")

    run = sub.add_parser("run", help="run one head on a goal")
    run.add_argument("goal", nargs="+")
    run.add_argument("--head", default="assistant")
    runtime_flags(run)

    swarm = sub.add_parser("swarm", help="run the multi-head team on a goal")
    swarm.add_argument("goal", nargs="+")
    swarm.add_argument("--no-critic", action="store_true", help="skip the critic review")
    runtime_flags(swarm)

    chat = sub.add_parser("chat", help="interactive chat with memory")
    chat.add_argument("--session", default="default")
    runtime_flags(chat)

    serve = sub.add_parser("serve", help="start the gateway: dashboard, API, channels, scheduler")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--provider")
    serve.add_argument("--model")

    init = sub.add_parser("init", help=f"create {CONFIG_FILENAME} and the workspace")
    init.add_argument("--force", action="store_true")

    doctor = sub.add_parser("doctor", help="check providers, tools, and configuration")
    doctor.add_argument("--provider")

    sub.add_parser("heads", help="list heads")
    tools = sub.add_parser("tools", help="list tools and their approval policy")
    runtime_flags(tools)

    runs = sub.add_parser("runs", help="list past runs or replay one")
    runs.add_argument("run_id", nargs="?")
    runs.add_argument("--limit", type=int, default=20)

    schedule = sub.add_parser("schedule", help="manage scheduled automations")
    schedule_sub = schedule.add_subparsers(dest="action", required=True)
    add = schedule_sub.add_parser("add")
    add.add_argument("goal", nargs="+")
    add.add_argument("--every", type=int, metavar="MINUTES")
    add.add_argument("--cron", metavar="EXPR", help='e.g. "0 9 * * 1-5"')
    add.add_argument("--swarm", action="store_true")
    add.add_argument("--head", default="assistant")
    add.add_argument("--name")
    add.add_argument("--notify", help="telegram:<chat_id> to receive results")
    schedule_sub.add_parser("list")
    remove = schedule_sub.add_parser("remove")
    remove.add_argument("id")

    memory = sub.add_parser("memory", help="manage long-term memory")
    memory.add_argument("action", choices=["list", "add", "search", "delete"])
    memory.add_argument("text", nargs="*")
    return parser


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        os.system("")  # enable ANSI escape handling in classic consoles
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError):
                pass
    args = build_parser().parse_args(argv)
    handlers = {
        "run": lambda: cmd_run(args, "agent"),
        "swarm": lambda: cmd_run(args, "swarm"),
        "chat": lambda: cmd_chat(args),
        "serve": lambda: cmd_serve(args),
        "init": lambda: cmd_init(args),
        "doctor": lambda: cmd_doctor(args),
        "heads": lambda: cmd_heads(args),
        "tools": lambda: cmd_tools(args),
        "runs": lambda: cmd_runs(args),
        "schedule": lambda: cmd_schedule(args),
        "memory": lambda: cmd_memory(args),
    }
    try:
        return handlers[args.command]()
    except KeyError as exc:
        print(color("red", f"Error: {exc}"), file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError) as exc:
        print(color("red", f"Error: {exc}"), file=sys.stderr)
        return 2
