---
name: aero-api
description: Call the SIL AERO API (v2) for AI audio processing on low-resource languages — ASR transcription (multi-model + IPA/phonetic), forced alignment, voice conversion, noise removal, audio enhancement, audio infilling, and speaker diarization. Use whenever you need to transcribe audio, align text to audio, denoise, convert or edit a voice, or drive any AERO endpoint. Covers auth, the async submit→poll pattern, and all /v2 endpoints.
---

# AERO API (v2)

REST API for AI-powered audio processing specialised in low-resource languages. All work is **asynchronous**: `POST` a JSON body to submit a job (202 → `{"task_id": "uuid"}`), then `GET` the same resource path with the task id until `state` is `SUCCESS` or `FAILURE`.

**This skill uses the `/v2` API exclusively.** Legacy no-prefix and `/v1` endpoints still exist on the server but are frozen; do not use them for new work.

## Environments (base URLs)

| Env | Base URL |
|---|---|
| **Prod** | `https://aero-async.multilingualai.com` |
| **Dev** | `https://aero-async-dev.multilingualai.com` |
| **Local** | `http://localhost:8000` (via `make project-up` in the `aero-api` repo) |

Frontend UI: `https://aero.multilingualai.com`. Interactive docs (Swagger) at `<base_url>/docs`; the authoritative spec is `<base_url>/openapi.json`. **Default to dev** for experiments unless the user asks for prod.

## Credentials

Auth is an OAuth2 password flow. Set these before invoking:

```bash
export AERO_API_USERNAME="your_username"      # NB: a username, not necessarily an email
export AERO_API_PASSWORD="your_password"
```

If you have a local `aero-api` checkout, the creds are usually in its `.env`:

```bash
source <(grep -E '^AERO_API_(USERNAME|PASSWORD)=' ~/SIL/aero-api/.env | sed 's/^/export /')
```

Ask the user where to find their credentials if not already set.

## Authentication

All endpoints require an `Authorization: Bearer <token>` header **except** `/health`, `/token`, and `GET /v2/transcriptions/languages`. Get a token from `/token` (unversioned; rate-limited to 5 req/min/IP):

```bash
TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${AERO_API_USERNAME}&password=${AERO_API_PASSWORD}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Python:

```python
import requests
base_url = "https://aero-async-dev.multilingualai.com"
r = requests.post(f"{base_url}/token", data={"username": USER, "password": PW})
token = r.json()["access_token"]          # {"access_token": "eyJ...", "token_type": "bearer"}
headers = {"Authorization": f"Bearer {token}"}
```

Tokens expire (default 30 min) — re-fetch on a 401.

## The async submit → poll pattern (the core concept)

1. **Submit** with `POST /v2/<resource>` (JSON body) → `202` `{"task_id": "uuid"}`. An optional `Idempotency-Key` header makes retries of the same submit safe.
2. **Poll** `GET /v2/<resource>/{task_id}` until done.

Every status response is a **JSON envelope** — no binary responses in v2:

```json
{"task_id": "abc123", "state": "SUCCESS", "result": {...}, "error": null}
```

| Situation | HTTP | Body |
|---|---|---|
| `PENDING` (queued) | 202 | envelope, `result` null |
| `STARTED` / `SUCCESS` / `FAILURE` | 200 | envelope; on FAILURE `error` is `{code, message}` |
| Unknown task id | 404 | `{code, message, details}` |
| Validation error on submit/poll | 422 | `{code, message, details}` |
| Transient backend error | 503 | `{code, message, details}` — just retry |

Note a **failed task is still HTTP 200** with `state: "FAILURE"` — branch on `state`, not the HTTP code.

```python
import time

def poll(base_url, headers, resource, task_id, timeout=300, interval=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{base_url}/v2/{resource}/{task_id}", headers=headers)
        if resp.status_code == 503:      # transient — retry
            time.sleep(interval); continue
        data = resp.json()
        if data.get("state") == "SUCCESS":
            return data["result"]
        if data.get("state") == "FAILURE":
            raise RuntimeError(f"{data['error']['code']}: {data['error']['message']}")
        time.sleep(interval)
    raise TimeoutError(f"{resource}/{task_id}")
```

## Supplying audio (JSON, not multipart)

v2 has **no multipart uploads**. Audio goes in the JSON body, exactly one of two ways per clip:

- `s3_path` — an S3 reference (`s3://bucket/key`). Preferred for anything beyond a short clip.
- `audio_base64` + `audio_format` (e.g. `"mp3"`, `"wav"`) — inline base64, capped at ~10 MB of encoded text. Convenience for small audio.

Single-clip endpoints (noise removal, enhancement, infilling) take these fields **flat** at the top level. Multi-clip endpoints (transcriptions, phonetic, forced alignment) take `s3_paths` (array of strings, max 1000) **or** `audio_clips` (array of `{s3_path | audio_base64 + audio_format}` objects) — a single clip is just a list of one. Voice conversion nests two clips as `source` and `target` objects.

## Retrieving audio results

Tasks that produce audio (voice conversion, noise removal, enhancement, infilling) return an `AudioResult`:

```json
{"audio_url": "https://...presigned...", "log_id": 123, "format": "wav", "duration": 12.3}
```

Download the audio from the presigned `audio_url` with a plain GET (no auth header needed):

```python
result = poll(base_url, headers, "noise-removals", task_id)
open("out.wav", "wb").write(requests.get(result["audio_url"]).content)
```

## Endpoints

| Service | Submit | Poll | Result |
|---|---|---|---|
| Transcribe (ASR, 1–1000 clips) | `POST /v2/transcriptions` | `GET /v2/transcriptions/{id}` | `{items: [...], total}` |
| Phonetic / IPA | `POST /v2/phonetic-transcriptions` | `GET /v2/phonetic-transcriptions/{id}` | `{items: [...], total}` |
| Recommend language | `POST /v2/language-recommendations` | `GET /v2/language-recommendations/{id}` | JSON (may return immediately on exact match) |
| List ASR languages | `GET /v2/transcriptions/languages` | — | JSON (no auth) |
| Forced alignment | `POST /v2/forced-alignments` | `GET /v2/forced-alignments/{id}` | JSON |
| Forced align (HF dataset) | `POST /v2/forced-alignment-datasets` | `GET /v2/forced-alignment-datasets/{id}` | JSON |
| Voice conversion | `POST /v2/voice-conversions` | `GET /v2/voice-conversions/{id}` | `AudioResult` |
| Noise removal | `POST /v2/noise-removals` | `GET /v2/noise-removals/{id}` | `AudioResult` |
| Audio enhancement | `POST /v2/audio-enhancements` | `GET /v2/audio-enhancements/{id}` | `AudioResult` |
| Audio infilling | `POST /v2/audio-infillings` | `GET /v2/audio-infillings/{id}` | `AudioResult` |
| Speaker diarization (HF dataset) | `POST /v2/speaker-diarizations` | `GET /v2/speaker-diarizations/{id}` | JSON |
| Admin: ASR models | `GET/POST/PUT/DELETE /v2/asr/models[/{model_id}]` | — | JSON (admin only) |
| Admin: task list | `GET /v2/admin/tasks` (filter by username/state/date, paginated) | — | JSON (admin only) |
| Health | `GET /health` | — | JSON (no auth, unversioned) |

There is no separate batch endpoint — `/v2/transcriptions` is batch-native (`items` in the result carry a `filename` per clip). Rating submission has no v2 endpoint yet; the legacy `POST /asr/rating` is the only surface for it.

## Quick recipes

### Transcribe (ASR)

```python
import base64

# method: w2v-bert (default) | whisper | mms | omnilingual | phonetic
audio_b64 = base64.b64encode(open("audio.mp3", "rb").read()).decode()
r = requests.post(f"{base_url}/v2/transcriptions", headers=headers, json={
    "audio_clips": [{"audio_base64": audio_b64, "audio_format": "mp3"}],
    # or: "s3_paths": ["s3://bucket/audio.mp3"],
    "language_iso": "spa", "method": "mms", "s3_upload": False})
task_id = r.json()["task_id"]
result = poll(base_url, headers, "transcriptions", task_id)
print(result["items"][0]["transcription"])   # items: [{transcription, method, log_id, confidence, filename, ...}]
```

Key body fields: `language_iso` (required, ISO 639-3, e.g. `bcc_Latn`), `method`, `romanize` (default false), `timestamp_level` (`chunk`|`word`|`character`), `best_quality` (w2v-bert: run all active models), `timestamps` (list of seconds — split a single clip at these points and transcribe each segment). `GET /v2/transcriptions/languages` lists ~1600 languages; filter with `?language_iso=bcc_Latn`.

### Word-level timestamps (needed for infilling text edits)

`POST /v2/phonetic-transcriptions` with `language_iso` + `"timestamp_level": "word"`; the per-clip word timings (`[{"word","start","end"}, ...]`) feed `word_times` for audio infilling. `guidance_method` picks the ASR model used for word boundaries (`mms` default).

### Forced alignment

```python
r = requests.post(f"{base_url}/v2/forced-alignments", headers=headers, json={
    "s3_paths": ["s3://bucket/audio.mp3"],           # or "audio_clips": [{...}]
    "ref_texts": ["En el principio"],                 # one per clip, same order
    "romanize": False, "s3_upload": False})
result = poll(base_url, headers, "forced-alignments", r.json()["task_id"])
```

Each `ref_texts` entry may be a plain string, a list of strings, or structured `{key, text}` segments. `POST /v2/forced-alignment-datasets` aligns a whole Hugging Face dataset (`dataset_name`, `text_column`, `audio_column`, ...).

### Voice conversion

```python
# model: freevc (default, A10G) | seed_vc (zero-shot) | playdiffusion (experimental)
r = requests.post(f"{base_url}/v2/voice-conversions", headers=headers, json={
    "source": {"s3_path": "s3://bucket/source.mp3"},
    "target": {"audio_base64": tgt_b64, "audio_format": "mp3"},
    "model": "freevc"})
result = poll(base_url, headers, "voice-conversions", r.json()["task_id"])
open("converted.wav", "wb").write(requests.get(result["audio_url"]).content)
```

`source` and `target` are each an `AudioSource` object (`s3_path` or `audio_base64`+`audio_format`); mixing styles between the two is fine.

### Noise removal

```python
# method: sam (default; text-prompted isolation, supports prompt=, quality=standard|high) | mpnet (general)
r = requests.post(f"{base_url}/v2/noise-removals", headers=headers, json={
    "s3_path": "s3://bucket/noisy.wav", "method": "mpnet"})
result = poll(base_url, headers, "noise-removals", r.json()["task_id"])
```

### Audio enhancement

Resemble-enhance denoise + CFM enhancement, defaults tuned for Scripture audio:

```python
r = requests.post(f"{base_url}/v2/audio-enhancements", headers=headers, json={
    "s3_path": "s3://bucket/audio.wav",
    "nfe": 64, "solver": "midpoint", "lambd": 0.9, "tau": 0.2,   # defaults shown
    "denoise_only": False})
```

`tau=0.2` is deliberate — the library default of 0.5 can hallucinate phonemes. `denoise_only: true` skips the CFM stage.

### Audio infilling

Two modes — **splice audio clips** via `replacements`, or **change spoken words** via `modified_text`. Replacement audio is carried inline per replacement (no separate uploads):

```python
# Splice: replacements = array of {start, end, audio_s3_path | audio_base64 + audio_format}
r = requests.post(f"{base_url}/v2/audio-infillings", headers=headers, json={
    "s3_path": "s3://bucket/source.wav",
    "replacements": [{"start": 1.15, "end": 1.68, "audio_s3_path": "s3://bucket/clip.mp3"}]})

# Text edit: send the FULL target transcript in modified_text + the original input_text + word_times.
# word_times is REQUIRED for text edits (get it from /v2/phonetic-transcriptions, timestamp_level="word").
r = requests.post(f"{base_url}/v2/audio-infillings", headers=headers, json={
    "s3_path": "s3://bucket/source.wav",
    "input_text": "...original...", "modified_text": "...full target...",
    "word_times": word_times})
```

There is **no** per-replacement `text` field — to change words, use `modified_text`. A text edit without `word_times` fails with a Modal "zero-length tensor" error (that's the missing timings, not a bad audio file).

## Gotchas

- **v2 is JSON everywhere** — no multipart uploads, no raw-binary status responses. Audio in: `s3_path`/`audio_base64`. Audio out: presigned `audio_url` in `result`.
- **A failed task is HTTP 200** with `state: "FAILURE"` and `error: {code, message}` — branch on `state`. 404 = unknown/expired task id; 503 = transient, retry.
- Inline `audio_base64` is capped (~10 MB encoded) — use `s3_path` for anything bigger.
- Noise removal's default `method` is `sam` (v1 defaulted to `mpnet`) — pass `method` explicitly if you care.
- Tokens expire (~30 min) → re-auth on 401. `/token` is rate-limited (5/min/IP).
- `language_iso` for ASR is ISO 639-3, optionally with script suffix (`bcc_Latn`); wrong/unsupported codes are a common failure. Use `/v2/language-recommendations` to find the closest supported language.
- Diarization and forced-alignment-datasets operate on **Hugging Face datasets**, not audio clips.
- Send an `Idempotency-Key` header on submits you might retry.
- `/openapi.json` is authoritative — consult it before assuming a param name or response shape; v2 can still evolve.
