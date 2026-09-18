#!/bin/bash
# ClearML REST helpers for the SIL server.
#
# Basic auth 401s on most endpoints: POST auth.login with HTTP Basic, then use the
# returned token as Bearer for everything else.
#
#   source clearml_helpers.sh
#   T=$(get_token)
#   workers "$T"
#   task_status "$T" <task_id>
#   task_log "$T" <task_id> 200
#   queues "$T"
#
# Credentials: CLEARML_API_ACCESS_KEY / CLEARML_API_SECRET_KEY, or the older
# CLEARML_ACCES_KEY (sic) / CLEARML_SECRET_KEY used in several repo .env files.

API="${CLEARML_API_HOST:-https://api.sil.hosted.allegro.ai}"

get_token() {
  local key="${CLEARML_API_ACCESS_KEY:-$CLEARML_ACCES_KEY}"
  local secret="${CLEARML_API_SECRET_KEY:-$CLEARML_SECRET_KEY}"
  if [ -z "$key" ] || [ -z "$secret" ]; then
    echo "Set CLEARML_API_ACCESS_KEY/CLEARML_API_SECRET_KEY (or source the repo .env)" >&2
    return 1
  fi
  curl -s -u "$key:$secret" -X POST "$API/auth.login" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])"
}

task_status() {
  curl -s -H "Authorization: Bearer $1" -X POST "$API/tasks.get_by_id" \
    -H 'Content-Type: application/json' -d "{\"task\":\"$2\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['task']['status'])"
}

task_log() {
  curl -s -H "Authorization: Bearer $1" -X POST "$API/events.get_task_log" \
    -H 'Content-Type: application/json' \
    -d "{\"task\":\"$2\",\"order\":\"asc\",\"batch_size\":${3:-100},\"navigate_earlier\":true}" \
    | python3 -c "import sys,json;[print(e.get('msg','')) for e in json.load(sys.stdin)['data']['events']]"
}

workers() {
  curl -s -H "Authorization: Bearer $1" -X POST "$API/workers.get_all" \
    -H 'Content-Type: application/json' -d '{}' \
    | python3 -c "
import sys,json
for w in json.load(sys.stdin)['data']['workers']:
    t = w.get('task') or {}
    print(w['id'], '|', t.get('name') or 'IDLE')"
}

queues() {
  curl -s -H "Authorization: Bearer $1" -X POST "$API/queues.get_all" \
    -H 'Content-Type: application/json' -d '{}' \
    | python3 -c "
import sys,json
for q in json.load(sys.stdin)['data']['queues']:
    print(f\"{q['name']:<24} queued={len(q.get('entries') or [])}\")"
}

enqueue() {  # enqueue "$T" <task_id> <queue_name>
  curl -s -H "Authorization: Bearer $1" -X POST "$API/tasks.enqueue" \
    -H 'Content-Type: application/json' -d "{\"task\":\"$2\",\"queue_name\":\"$3\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['meta']['result_msg'])"
}
