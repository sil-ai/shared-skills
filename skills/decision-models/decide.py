"""Minimal stdlib client for OpenRouter's Decisions endpoint (Jev and friends).

    from decide import ask
    res = ask({"text": "..."}, {"is_spam": {"type": "noul", "instructions": "Is this spam?"}})
    res["answers"]["is_spam"]["noul"]

Reads OPENROUTER_API_KEY from the environment, falling back to ./.env.
"""
import functools
import json
import os
import time
import urllib.error
import urllib.request

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"
RETRY = (402, 408, 429, 500, 502, 503, 529)


class StateTooLong(Exception):
    """State + questions exceeded the model's context: trim and retry."""


@functools.cache
def _key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    raise SystemExit("OPENROUTER_API_KEY not set (env or ./.env)")


def _backoff(e, attempt):
    try:
        return float(e.headers.get("Retry-After"))
    except (TypeError, ValueError):
        return 2 ** attempt


def ask(state, questions, model=MODEL, retries=6):
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    key = _key()
    for attempt in range(retries):
        req = urllib.request.Request(URL, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:500]
            if e.code == 422 or (e.code == 400 and "max_tokens_exceeded" in detail):
                raise StateTooLong(detail)
            if e.code in RETRY and attempt < retries - 1:
                time.sleep(_backoff(e, attempt))
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}")
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def ask_pair(state, a, b, question, model=MODEL):
    """Pairwise choice asked in both slot orders, probabilities averaged to cancel position bias.

    `question` is a choice question whose criteria keys are "a", "b" (and optionally "tie"),
    referring to state fields `candidate_a` / `candidate_b`. Returns {"a": p, "b": p, ...}.
    """
    if not {"a", "b"} <= set(question["criteria"]) <= {"a", "b", "tie"}:
        raise ValueError(f"ask_pair needs criteria keys a/b(/tie), got {sorted(question['criteria'])}")
    fwd = ask({**state, "candidate_a": a, "candidate_b": b}, {"q": question}, model)
    rev = ask({**state, "candidate_a": b, "candidate_b": a}, {"q": question}, model)
    p1, p2 = fwd["answers"]["q"]["probabilities"], rev["answers"]["q"]["probabilities"]
    swap = {"a": "b", "b": "a"}
    return {k: (p1[k] + p2[swap.get(k, k)]) / 2 for k in p1}


if __name__ == "__main__":
    print(json.dumps(ask(
        {"text": "The build failed with a segfault in libfoo."},
        {"is_error": {"type": "noul", "instructions": "Does the text report a failure?",
                      "criteria": {"true": "It reports a failure", "false": "It does not"}}}),
        indent=2))
