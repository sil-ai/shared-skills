---
name: loki-logs
description: Query the multilingualai observability logs (and metrics/traces) via the `observability` MCP server. Use when the user wants to inspect production/dev logs, debug a failing service (aero-api, aqua-api, translation-tts-app, etc.), or check what is happening across the observability stack.
---

# Loki Logs

Query the multilingualai observability data through the **`observability`
MCP server** (`grafana/mcp-grafana`), which talks to Grafana and exposes
logs (Loki), metrics (Prometheus) and traces (Tempo) as Claude tools.
There is no local script — the MCP is the single, shared query path.

## Prerequisite: connect the MCP once

```bash
claude mcp add --transport http observability \
  https://observability.multilingualai.com/mcp \
  --header "Authorization: Bearer $MCP_TOKEN"
```

Get `MCP_TOKEN` from whoever runs the observability stack. Confirm the
connection with `/mcp` — it should list `observability` and its tools.
Nothing else is needed: no repo clone, no `LOKI_TOKEN` in your shell.

## What the MCP can do

The `observability` MCP is not just logs. Through Grafana it can query
the whole stack, read-only:

- **Logs (Loki)** — search log lines with LogQL, list labels, find
  patterns.
- **Metrics (Prometheus)** — run PromQL instant/range queries, list
  metric names and labels, compute histogram percentiles.
- **Traces (Tempo)** — look up distributed traces and investigate slow
  requests.
- **Datasources & dashboards** — list datasources, check their health,
  read existing dashboards.

It cannot write, page, or change anything (no alerting/oncall/admin).
Just ask in plain language — e.g. *"errors in aero-api in the last
hour"* or *"CPU usage for aqua-api today"* — and Claude picks the right
tool. The rest of this doc focuses on the log side.

## Log tools

- `query_loki_logs` — run LogQL (log or metric queries) against Loki.
  Takes `datasourceUid` (use `loki`), a LogQL expression, a time range,
  and a limit.
- `list_loki_label_names` — available label names (`container_id`,
  `environment`, `project`).
- `list_loki_label_values` — values for a label (e.g. every active
  `project`).
- `query_loki_patterns` — detected log patterns / common structures.
- `query_loki_stats` — stream/chunk stats for a selector.

For metrics use `query_prometheus`; traces have their own Tempo tools.

## Known projects (label `project`)

`aero-api`, `aero-django-app`, `aqua-agent`, `aqua-api`, `aqua-assessments`,
`aqua-django-app`, `faithbridge-obt-django-app`, `gmo-ai-copilot`,
`translation-tts-app`.

Call `list_loki_label_values` on `project` to refresh this list — it can
change.

## Environments (label `environment`)

`main`, `release`, `development`. Not every project has every
environment; list the `environment` values or query to see live
combinations.

## Log line format

Most services log structured JSON, e.g.:

```json
{"level": "INFO", "logger": "middleware", "message": "GET /latest/train/status 200 OK 13ms user=dev@paratext.org"}
{"level": "ERROR", "logger": "services.audio_infilling", "message": "...traceback..."}
```

So a typical LogQL query filters by label and then parses JSON, e.g.
`{project="aero-api", environment="main"} | json | level="ERROR"`. Put
line filters (`|= "..."` / `|~ "..."`) before `| json` — they prune on
raw bytes and keep queries cheap.

## Workflow

1. **Scope it.** Filter by `project` (and `environment` if known). For
   problems, filter on `level` (`ERROR`, `WARNING`). Unsure what's
   active? List `project` values first.
2. **Query.** Start with a modest time range and limit, widen if empty.
   A single query can look back at most 7 days (server-side
   `max_query_length`); use narrower windows.
3. **Summarize.** Group repeated errors, surface tracebacks, cite
   timestamps. Don't dump hundreds of raw lines — summarize and show the
   relevant ones.

## Notes

- Loki is log search, not dashboards — just log lines and simple metrics.
- The MCP is read-only; it cannot modify anything in the stack.
- To correlate a log line with its trace, look for a `trace_id` field and
  pivot to the Tempo tools.
