# Architecture

Agentic 0.2 is built around one `Runtime` that every surface shares: the CLI,
the gateway's dashboard and API, the Telegram channel, and the scheduler. All of
them start runs the same way and produce the same event log.

```text
 CLI ─┐                                         ┌─► Ollama / OpenAI-compatible / Anthropic
 API ─┤                                         │
 Dashboard ─┼─► Runtime ─► Swarm ─► Heads ──────┤
 Telegram ──┤      │         (planner,          ├─► ToolRegistry ─► ApprovalGate ─► tools / MCP
 Scheduler ─┘      │          critic,           │
                   │          synthesizer)      └─► Store (SQLite): memories, runs, events,
                   └─► EventBus ──► Store, CLI renderer, SSE stream, channels      chats, schedules
```

## Runs

A run is either a single head (`agent` mode) or a swarm (`swarm` mode).
`Runtime.run` creates a run record, emits `run.start`, executes the run, saves
the result, and emits `run.finish`. Exceptions and cancellations are recorded
in the run's status. They do not crash the process.

## The head loop

`agentic/agent.py` implements one head:

1. Build the system prompt. It contains the head's profile, the environment
   (time, OS, workspace, and the heads it can delegate to), the trust rules,
   skills that match the task, and the three most relevant memories.
2. Call the provider with the tools the head is allowed to use.
3. If the model calls tools, validate and execute each call through the
   registry, then add the results back to the conversation.
4. If the model replies without tool calls, that reply is the answer. An empty
   reply gets one retry, with a request for a plain-text answer.
5. If the step budget runs out, ask once more, with tools disabled, for the
   model's best final answer.

If the model repeats exactly the same tool call more than three times, the call
is skipped and the model is told to change its approach.

## The swarm

`agentic/swarm.py`:

1. **Plan.** The planner head receives the goal and a list of the worker heads,
   and must reply with a JSON task list. `normalize_plan` repairs the reply:
   unknown heads become `assistant`, empty tasks are dropped, duplicate IDs are
   renamed, and a task may only depend on tasks listed before it. This rule makes
   cycles impossible. After two invalid replies, the whole goal becomes a single
   assistant task.
2. **Execute.** Tasks whose dependencies are complete start immediately, up to
   `limits.max_parallel` at once. Each task receives the outputs of its
   dependencies, truncated to fit the context window. If a task crashes, it is
   recorded as failed and the tasks that depend on it still run, with a
   "(INCOMPLETE OR FAILED)" marker on that input.
3. **Critique.** The critic reviews all results against the goal and returns
   `{"approved", "feedback", "redo": [{"id", "instructions"}]}`. Each task in
   `redo` runs again with its previous output and the critic's instructions, for
   at most `limits.max_revisions` rounds.
4. **Synthesize.** The synthesizer combines the results into the final answer.
   When the plan has only one task, its output is used directly.

## Tools and approvals

`ToolRegistry.call` performs every check in order. It looks up the tool and
confirms the head is allowed to use it. It validates the arguments against the
tool's schema and rejects unknown ones. It asks `ApprovalGate.check`, which
uses the policy for the tool's tier: `auto`, `ask`, or `deny`. Next come any
grants for the current run, then the unattended rule for `schedule:` runs.
Only then is the approver asked. Finally, the registry runs the tool with a
timeout. Blocking tools run in a worker thread so that parallel heads stay
concurrent. Errors and timeouts become results that the model can read, and the
output is truncated.

Approvers:

- **Terminal:** an `input()` prompt. A lock keeps prompts from parallel heads
  from interleaving.
- **Gateway:** `PendingApprovals`, which keeps pending requests as futures. The
  dashboard and Telegram resolve them.
- **None attached:** `ask` means deny.

## MCP

`agentic/tools/mcp.py` is a stdio JSON-RPC client. It performs the `initialize`
handshake, lists tools (following pagination), calls tools, maps `isError` to a
tool error, and ignores non-JSON lines that a server prints to stdout. Each MCP
tool is registered as `mcp__<server>__<tool>` under the permission tier set for
its server.

## Persistence

`agentic/store.py` keeps everything in one SQLite file (`.agentic/agentic.db`).
It uses WAL mode and a lock so worker threads can share it safely. Memory search
uses an FTS5 index, kept in sync by triggers and ranked by BM25. If the SQLite
build has no FTS5, search falls back to `LIKE` matching.

## Events

Event types:

`run.start`, `run.finish`, `head.start`, `head.thought`, `head.finish`,
`head.error`, `tool.call`, `tool.result`, `swarm.plan`, `swarm.plan_invalid`,
`task.start`, `task.finish`, `critic.verdict`, `swarm.revision`,
`approval.requested`, `approval.resolved`.

Every event is stored with its run ID. The CLI prints events as they happen,
`/api/stream` sends them to the dashboard, and `agentic runs <id>` replays them.

## Gateway

The gateway is a FastAPI app with a lifespan that starts the MCP servers, the
Telegram channel, and the scheduler. Middleware rejects requests that have a
cross-origin `Origin` header. When the gateway is bound to loopback, it also
rejects requests whose `Host` header is not a loopback name, which blocks DNS
rebinding. When `AGENTIC_TOKEN` is set, every `/api` route requires a bearer
token. The event stream also accepts the token as a `?token=` query parameter,
because `EventSource` cannot send headers.

## Legacy surfaces

The v0.1 desktop agent (`main.py`, `core/`, `perception/`, `execution/`,
`planning/`) and the React chat app (`agentic-app/`) remain in the repository.
The skill registry moved to `agentic/skills.py`. `core/skills.py` re-exports it
so the legacy code keeps working.
