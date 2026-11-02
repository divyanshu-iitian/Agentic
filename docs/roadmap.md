# Roadmap

## Now

- stream model tokens to the dashboard and terminal
- MCP over Streamable HTTP, in addition to stdio
- an evaluation harness: task completion, unsafe-action rejection, and recovery,
  judged by the resulting state
- per-head cost and token budgets with usage totals in Mission Control
- container or VM sandboxing for `run_command` and `run_python`

## Next

- more channels: Discord, Slack, email, and a generic webhook
- accessibility-tree desktop automation on Windows (UI Automation) and macOS
- vector memory as an optional complement to FTS5
- reusable, parameterized swarm templates ("playbooks")
- signed head and skill metadata with trust levels

## Later

- packaged desktop builds for Windows, Linux, and macOS
- a reviewed community registry for heads, skills, and MCP presets
- multi-user gateway with per-user permissions and audit export

Features move out of the roadmap only after documentation and repeatable tests
land with the implementation.
