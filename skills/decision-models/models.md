# Decision-model landscape (checked 2026-09-29)

The category is weeks old and moving fast. Re-list before relying on this:
`curl -s "https://openrouter.ai/api/v1/models?output_modalities=decisions"`.

## On OpenRouter's Decisions endpoint

All of these use the same `POST /api/alpha/decisions` shape, and output tokens are free for all of them. Latency is what we measured through OpenRouter.

| id | maker / basis | context | input $/M | latency | use it for |
|---|---|---|---|---|---|
| `typesafe/jev-1.13` (`~typesafe/jev-latest`) | TypeSafe, flagship "System One" model | 32k | 0.042 | 0.14–0.32 s | **Default.** All three question types, best-calibrated, fastest. |
| `upstage/solar-decide` | Upstage, Solar Mini 4 | **512k** | 0.05 | 6–15 s | State too big for Jev, or strong Korean. Slow, with ~1k tokens of overhead per request. |
| `respan/span-01` | Respan, eval/guardrail behaviour scoring | — | 0.02 | 0.5–0.7 s | Scoring agent traces. See the restrictions below. |
| `respan/span-01-lite` (`:free`) | Respan | — | 0 | 0.5–0.7 s | Free Span-01. Gave identical numbers in our test. |
| `jaredpalmer/kev-4b` | Jared Palmer, open weights (Qwen3.5-4B + LoRA, Apache-2.0) | 8k | 0.042 | 4.5–20 s | Checking a self-hostable model before deploying it. Weaker calibration. |

**Respan restrictions:** noul questions only, with plain-string instructions and criteria. The state must be a string or `{"input": [{role, content}...], "output": {"role": "assistant", "content": ...}}`. Anything else returns a descriptive 400.

**Not a decision endpoint:** `typesafe/jev-router` is a *chat-completions* router. Jev classifies each chat request and forwards it to the cheapest adequate model. You pay the routed model's price. Restrict its pool with `plugins: [{id: "jev-router", models: [...]}]`.

## Self-host / open weights (not on OpenRouter)

- **Kev** 0.8B / 4B / 9B / 27B: https://github.com/jaredpalmer/kev. Kev-27B scores 0.866 on JevBench.
- **Together Tev1-4B / 0.8B-experimental:** returns one option letter for 2–24 options. https://huggingface.co/togethercomputer/Tev1-4B-experimental
- **Mapika decider-4b / 2b** (Qwen3.5-4B); OceanLabs Coral-decider-4b is its successor.
- **djev** (Matt Mastracci): Jev-style decisions on DiffusionGemma, **with image input**. https://github.com/mmastrac/djev
- **Fastino GLiNER2.5-Decide** (340M encoder, 38–167 ms), CLM 8B, Convai Laya: https://systemonemodels.org/

These fit the case where data must stay on our own GPUs (Modal/ClearML). Validate them against Jev on labelled data first.

## Announced, not yet usable

**OpenAI Decisions API** (DevDay, 2026-09-29, limited preview): a specialised GPT-6 Luna claiming ~150 ms, text or image input, closed answer set, returns probabilities. The schema, id and price are unconfirmed. Image input would be the reason to try it.

## Older style: classifiers on `/chat/completions`

These guardrail models return text labels rather than probabilities: `openai/gpt-oss-safeguard-20b`, `nvidia/nemotron-3.5-content-safety`, `meta-llama/llama-guard-4-12b`. Use them only for policy-safety moderation that they were trained on.

## Benchmarks (vendor or third-party, unverified)

- JevBench (https://jevbench.dev): several 4B open models edge out Jev 1.13 on its items.
- Respan's 11-model comparison had Jev best (0.932 accuracy), ahead of Tev1-4B (0.901) and Kev-4B (0.833).

Treat both as hints. Our own labelled data decides.
