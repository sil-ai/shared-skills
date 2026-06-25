#!/usr/bin/env python3
"""Query Grafana Loki logs for the multilingualai observability stack.

Credentials come from the LOKI_URL and LOKI_TOKEN environment variables. If
they are not set (e.g. a non-interactive shell that never sourced ~/.bashrc),
they are read from the `export LOKI_URL=`/`export LOKI_TOKEN=` lines in
~/.bashrc as a fallback.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request


def get_creds():
    url = os.environ.get("LOKI_URL")
    token = os.environ.get("LOKI_TOKEN")
    if not (url and token):
        bashrc = os.path.expanduser("~/.bashrc")
        if os.path.exists(bashrc):
            text = open(bashrc).read()
            if not url:
                m = re.search(r'^export LOKI_URL=(.+)$', text, re.M)
                if m:
                    url = m.group(1).strip().strip('"\'')
            if not token:
                m = re.search(r'^export LOKI_TOKEN=(.+)$', text, re.M)
                if m:
                    token = m.group(1).strip().strip('"\'')
    if not (url and token):
        sys.exit("error: LOKI_URL / LOKI_TOKEN not set and not found in ~/.bashrc")
    return url.rstrip("/"), token


def api_get(path, params=None):
    url, token = get_creds()
    full = url + path
    if params:
        full += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(full, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def ns(seconds_ago):
    return str(int((time.time() - seconds_ago) * 1e9))


DURATION_RE = re.compile(r'^(\d+)([smhdw])$')
UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_since(s):
    m = DURATION_RE.match(s)
    if not m:
        sys.exit(f"error: bad --since '{s}', use e.g. 30m, 6h, 2d")
    return int(m.group(1)) * UNIT_SECONDS[m.group(2)]


def cmd_labels(args):
    data = api_get("/loki/api/v1/labels")["data"]
    print("\n".join(data))


def cmd_values(args):
    data = api_get(f"/loki/api/v1/label/{args.label}/values")["data"]
    print("\n".join(data))


def cmd_series(args):
    secs = parse_since(args.since)
    data = api_get("/loki/api/v1/series", {
        "match[]": '{project=~".+"}',
        "start": ns(secs),
        "end": ns(0),
    })["data"]
    rows = sorted({(s.get("project", "?"), s.get("environment", "?")) for s in data})
    for proj, env in rows:
        print(f"{proj:30} {env}")


def build_query(args):
    if args.query:
        return args.query
    selectors = []
    if args.project:
        selectors.append(f'project="{args.project}"')
    if args.env:
        selectors.append(f'environment="{args.env}"')
    if not selectors:
        selectors.append('project=~".+"')
    q = "{" + ", ".join(selectors) + "}"
    if args.level:
        levels = "|".join(l.strip().upper() for l in args.level.split(","))
        q += f' | json | level=~"{levels}"'
    if args.grep:
        q += f' |~ "{args.grep}"'
    return q


def cmd_query(args):
    secs = parse_since(args.since)
    query = build_query(args)
    data = api_get("/loki/api/v1/query_range", {
        "query": query,
        "start": ns(secs),
        "end": ns(0),
        "limit": str(args.limit),
        "direction": "backward",
    })["data"]["result"]

    entries = []
    for stream in data:
        labels = stream["stream"]
        for ts, line in stream["values"]:
            entries.append((int(ts), labels, line))
    entries.sort(key=lambda e: e[0], reverse=not args.asc)
    if args.asc:
        entries.reverse()

    if args.raw:
        for _, _, line in entries:
            print(line)
        return

    if not entries:
        print(f"(no log lines for `{query}` in the last {args.since})")
        return
    print(f"# query: {query}\n# {len(entries)} lines (last {args.since})\n")
    for tsns, labels, line in entries:
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tsns / 1e9))
        proj = labels.get("project", "?")
        env = labels.get("environment", "?")
        msg = line
        try:
            obj = json.loads(line)
            lvl = obj.get("level", "")
            text = obj.get("message", line)
            logger = obj.get("logger", "")
            msg = f"[{lvl:7}] {text}" + (f"  ({logger})" if logger else "")
        except (ValueError, TypeError):
            pass
        print(f"{when}  {proj}/{env}  {msg}")


def main():
    p = argparse.ArgumentParser(description="Query Grafana Loki logs.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("labels", help="list available label names")

    pv = sub.add_parser("values", help="list values for a label")
    pv.add_argument("label")

    ps = sub.add_parser("series", help="list active project/environment streams")
    ps.add_argument("--since", default="24h")

    pq = sub.add_parser("query", help="fetch log lines")
    pq.add_argument("--project")
    pq.add_argument("--env")
    pq.add_argument("--level", help="comma-separated, e.g. ERROR,WARNING")
    pq.add_argument("--grep", help="regex line filter")
    pq.add_argument("--query", help="raw LogQL (overrides the flags above)")
    pq.add_argument("--since", default="1h")
    pq.add_argument("--limit", type=int, default=100)
    pq.add_argument("--asc", action="store_true", help="oldest first")
    pq.add_argument("--raw", action="store_true", help="print raw log lines only")

    args = p.parse_args()
    {"labels": cmd_labels, "values": cmd_values,
     "series": cmd_series, "query": cmd_query}[args.cmd](args)


if __name__ == "__main__":
    main()
