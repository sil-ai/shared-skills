---
name: decision-models
description: Use System One / decision models (TypeSafe Jev, Upstage Solar Decide, Respan Span-01, Kev) — fast, cheap models that return calibrated probabilities instead of text, called via OpenRouter's Decisions endpoint. Use when a step needs a yes/no, pick-one-of-N, or rubric-score judgment at scale (classify, route, triage, gate an agent or tool call, detect defects in LLM/MT output, pick the better of two candidates, rerank), or when an LLM prompt-and-parse step could become a typed decision. Covers the endpoint, request/response shapes, question design, usage patterns, and model choice.
---

# Decision models (System One)

A **decision model** is to an LLM what a comparator is to a CPU: it never generates text. You send a `state` (any JSON: the facts) plus named, typed `questions`, and get probabilities back in ~150–300 ms for fractions of a cent. Code owns the workflow; the model supplies the judgment where plain code would need semantic understanding.

Reach for one when the answer is a **closed set**: yes/no, one-of-N, or a level on an ordered rubric. When the step needs free text, reasoning, arithmetic, counting, or date comparison, use an LLM or code instead.

## Calling it

Decision models are **not** on `/chat/completions` (Jev returns 400 "is a decisions model") and are **hidden from `/api/v1/models`**. List them with `GET https://openrouter.ai/api/v1/models?output_modalities=decisions`.

- `POST https://openrouter.ai/api/alpha/decisions`
- `Authorization: Bearer $OPENROUTER_API_KEY` (or in the project's `.env`, which `decide.py` reads)
- Body: `{model, state, questions}`, plus optional `session_id`, `user`, `trace`, `provider`. There are **no** sampling params: no temperature, logprobs, tools or response_format.
- Default model: `typesafe/jev-1.13` (pin it). `~typesafe/jev-latest` floats, and the tilde is required.

```json
{"model": "typesafe/jev-1.13",
 "state": {"text": "The build failed with a segfault in libfoo."},
 "questions": {
   "is_error": {"type": "noul", "instructions": "Does the text report a failure?",
                "criteria": {"true": "It reports a failure", "false": "It does not"}},
   "severity": {"type": "score", "instructions": "How severe is the problem?",
                "criteria": ["low", "medium", "high"]},
   "kind":     {"type": "choice", "instructions": "Which kind of issue is it?",
                "criteria": {"crash": "process crash", "perf": "slowness", "docs": "documentation"}}}}
```

```json
{"model": "typesafe/jev-1.13-20260917",
 "answers": {
   "is_error": {"type": "noul", "noul": 0.99},
   "severity": {"type": "score", "score": 1.9, "legend": {"0": "low", "1": "medium", "2": "high"},
                "probabilities": {"0": 0, "1": 0.09, "2": 0.91}, "confidence": 0.85},
   "kind":     {"type": "choice", "choice": "crash",
                "probabilities": {"crash": 1, "perf": 0, "docs": 0}, "confidence": 1}},
 "usage": {"input_tokens": 410, "output_tokens": 70, "cost": 0.00001722},
 "id": "gen-dec-...", "provider": "TypeSafe"}
```

| type | criteria | answer |
|---|---|---|
| `noul` | `{"true": ..., "false": ...}` | `noul` = P(yes). No confidence field. |
| `choice` | `{option: description}`, up to 255 | `choice`, `probabilities`, `confidence` |
| `score` | ordered list of 2–10 levels, worst→best | `score` = expected 0-based index, `probabilities`, `legend`, `confidence` |

`confidence` = `clip((n·p_max − 1)/(n − 1), 0, 1)`. It measures how concentrated the distribution is, not whether the answer is correct.

`decide.py` in this folder is a stdlib-only client with the retry and error handling below: `from decide import ask`. Python and JS SDKs also exist (`typesafe_sdk`, `@typesafe-ai/sdk`). Point them at OpenRouter with `TYPESAFE_BASE_URL=https://openrouter.ai/api` and your OpenRouter key.

### Errors and limits

- **Context:** 32k tokens for Jev. Overflow comes back as **`400 max_tokens_exceeded`**, not 422, so catch both and trim the state.
- **Retries:** retry 408/429/5xx with backoff. OpenRouter also sends a transient **402** with `limit_source: "openrouter_in_flight_budget"`; retry that after `Retry-After`.
- **Concurrency:** 8–24 threads ran clean for us.
- **Cost:** $0.042/M input tokens, output free, and every response carries `usage.cost`. Each request carries about 270 tokens of overhead.

## Designing questions

- **Batch every independent question into one call.** Output is free and the overhead is per request. Questions run in parallel over the same state and cannot see each other's answers. Make a second call only when one answer decides what state or options come next.
- **One narrow judgment per question.** Put the judgment in `instructions` and define each answer in `criteria`. Write complete meaning into the question: its name is never sent to the model.
- **State is named JSON fields.** Reference fields in backticks from instructions (`` `translation` renders `source_text` ``). Keep the state lean: irrelevant material measurably lowers accuracy.
- **Include a no-match option** (`"none"`, `"tie"`) whenever nothing may fit.
- **Keep policy in code.** Store the raw probabilities, then apply thresholds, weights and "any serious defect" rules in code, where changing them needs no re-run. Tune thresholds on your own labelled data; a noul threshold does not transfer to a choice question.
- **Literal reader.** It handles double negatives, multi-hop indirection and contradictory criteria poorly. It is best in English and weaker in other languages. It can be prompt-injected through the state, so treat state from untrusted users as hostile.

## Patterns that work

- **Gate and select, don't measure.** Decision models are strongest at spotting clear defects (wrong language, wrong item, truncated, incoherent) and at choosing between candidates. They are weakest as an absolute quality score: a rubric `score` is fine for sorting or flagging, but not as a calibrated gauge across different sources or styles.
- **Compare instead of rating.** "Which of `candidate_a` / `candidate_b` is better?" is usually far more reliable than scoring each candidate separately and comparing the scores. Use it for best-of-N selection, reranking and choosing between system outputs.
- **Cancel position bias.** Pairwise choices favour one slot regardless of content. Ask both orders and average the distributions. `ask_pair(state, a, b, question)` in `decide.py` does this. It puts the candidates in `candidate_a` / `candidate_b`, and the criteria keys must be `a`, `b` and optionally `tie`.
- **Ask for the defect directly.** A general quality score can reward the wrong thing; for example, an untranslated copy of the source can look "adequate". Ask a dedicated noul for each failure you care about, and combine the answers in code rather than hoping one question covers everything.
- **Show examples when the domain is unfamiliar.** For low-resource languages, niche jargon or house style, put a handful of verified examples in the state, e.g. `examples: [{input, good_output}]`. This supplies the prior the model lacks and can turn near-chance judgments into useful ones. More examples cost linearly and quickly stop helping; start around 10–20.
- **Validate before you trust.** Label a small sample of your real data, measure the model's accuracy, and pick thresholds from that before deploying. Typed output guarantees the format, not the truth.
- **Escalate the uncertain cases.** Let the model settle the confident cases cheaply, and send low-probability or low-confidence ones to an LLM or a person.

## Other models

For picking a model other than Jev — Upstage Solar Decide (512k context), Respan Span-01 (guardrails/eval scoring, noul only), open-weight Kev / Tev / decider models you can self-host, and OpenAI's newly announced Decisions API — read [`models.md`](models.md).

## Live docs

The TypeSafe docs are the source of truth for primitives, cookbooks and limits. Start at the index https://docs.typesafe.ai/llms.txt (any page is available as Markdown by appending `.md`). Before designing a new workflow, check the closest cookbook: rerank, citation check, function calling, hierarchical classification, extraction cascade. OpenRouter's guide is at https://openrouter.ai/docs/guides/community/jev.

When real use turns up a pattern or pitfall that applies beyond one project, add it to **Patterns that work**.
