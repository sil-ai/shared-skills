---
name: loki-logs
description: Query the multilingualai Grafana Loki logs for any project/environment - errors, request traces, tracebacks, recent activity. Use when the user wants to inspect production/dev logs, debug a failing service (aero-api, aqua-api, translation-tts-app, etc.), or check what is happening across the observability stack.
---

# Loki Logs

Queries the Grafana Loki instance at `https://observability.multilingualai.com`
for container/application logs across the multilingualai projects.

Credentials live in the `LOKI_URL` and `LOKI_TOKEN` environment variables
(auth is `Authorization: Bearer $LOKI_TOKEN`). These are exported in `~/.bashrc`,
so they may be absent in a non-interactive shell - the helper script reads them
from `~/.bashrc` as a fallback, so you don't need to source anything first.

## Invocation

This skill is user-invocable:

- `/loki-logs` - show what projects/environments are active and recent errors
- `/loki-logs <project>` - recent logs for a project, e.g. `/loki-logs aero-api`
- `/loki-logs <project> errors` - recent errors/warnings for a project
- Free-form, e.g. `/loki-logs why is translation-tts-app 500ing`

## Helper script

All access goes through `scripts/loki.py` (stdlib only, use system `python3`):

```bash
python3 ~/.claude/skills/loki-logs/scripts/loki.py <subcommand> [options]
```

### Subcommands

- `labels` - list label names (`container_id`, `environment`, `project`)
- `values <label>` - list values for a label (e.g. `values project`)
- `series [--since 24h]` - list active `project / environment` stream pairs
- `query [options]` - fetch log lines

### `query` options

- `--project <name>` - filter by project label
- `--env <name>` - filter by environment (`main`, `release`, `development`)
- `--level ERROR,WARNING` - JSON-parse and filter by log level (comma list)
- `--grep <regex>` - line-level regex filter (LogQL `|~`)
- `--query '<LogQL>'` - raw LogQL, overrides the flags above
- `--since 1h` - lookback window (`30m`, `6h`, `2d`, `1w`); default `1h`
- `--limit 100` - max lines (default 100)
- `--asc` - oldest first (default newest first)
- `--raw` - print raw JSON log lines only (no formatting)

## Known projects (label `project`)

`aero-api`, `aero-django-app`, `aqua-agent`, `aqua-api`, `aqua-assessments`,
`aqua-django-app`, `faithbridge-obt-django-app`, `gmo-ai-copilot`,
`translation-tts-app`.

Run `python3 .../loki.py values project` to refresh this list - it can change.

## Environments (label `environment`)

`main`, `release`, `development`. Not every project has every environment;
use `series` to see live combinations.

## Log line format

Most services log structured JSON, e.g.:

```json
{"level": "INFO", "logger": "middleware", "message": "GET /latest/train/status 200 OK 13ms user=dev@paratext.org"}
{"level": "ERROR", "logger": "services.audio_infilling", "message": "...traceback..."}
```

The `query` command pretty-prints these as
`timestamp  project/env  [LEVEL] message (logger)`. Multi-line tracebacks come
through in the `message` field. Use `--raw` if you need the full JSON.

## Workflow

1. **Scope it.** If the user named a project, filter with `--project`. If they
   want problems, add `--level ERROR,WARNING`. Otherwise start with `series`
   to see what is active.

2. **Query.** Start with a modest `--since`/`--limit` and widen if empty.

   ```bash
   # recent errors for one service
   python3 ~/.claude/skills/loki-logs/scripts/loki.py query \
     --project aero-api --level ERROR,WARNING --since 6h --limit 50

   # trace a request id across a project
   python3 ~/.claude/skills/loki-logs/scripts/loki.py query \
     --project aqua-api --grep "91463be8" --since 24h

   # raw LogQL for anything the flags can't express
   python3 ~/.claude/skills/loki-logs/scripts/loki.py query \
     --query '{project="translation-tts-app"} | json | status_code>=500' --since 12h
   ```

3. **Summarize.** Report what you found - group repeated errors, surface
   tracebacks, and cite timestamps. Don't dump hundreds of raw lines at the
   user; summarize and show the relevant ones.

## Notes

- Loki is log search, not metrics - there are no dashboards here, just lines.
- The token is a secret. Never echo `LOKI_TOKEN` or paste it into output.
- Timestamps from the API are UTC nanoseconds; the script renders them in local time.
