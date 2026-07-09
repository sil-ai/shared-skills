---
name: aero-api
description: Call the SIL AERO API for AI audio processing on low-resource languages — ASR transcription (multi-model + IPA/phonetic), forced alignment, voice conversion, noise removal, audio infilling, and speaker diarization. Use whenever you need to transcribe audio, align text to audio, denoise, convert or edit a voice, or drive any AERO endpoint. Covers auth, the async submit→poll pattern, endpoints, and v1/v2 versioning.
---

# AERO API

REST API for AI-powered audio processing specialised in low-resource languages. Most work is **asynchronous**: you `POST` to submit a job (get back a `task_id`), then `GET` the status endpoint until the task reaches `SUCCESS` or `FAILURE`.

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

All endpoints require a `Authorization: Bearer <token>` header **except** `/health`, `/token`, and `GET /asr/languages`. Get a token from `/token` (rate-limited to 5 req/min/IP):

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

1. **Submit** with `POST` → `{"task_id": "uuid"}` (batch also returns `num_files`).
2. **Poll** `GET .../{task_id}` until done.

| State | HTTP | Meaning |
|---|---|---|
| `PENDING` | 202 | Queued, not yet picked up |
| `STARTED` | 200 | Worker processing |
| `SUCCESS` | 200 | Complete |
| `FAILURE` | 200 or 500 | Failed |
| task not found | 404 | Invalid/expired `task_id` |

**Two response styles — this trips people up:**
- **ASR, forced alignment, diarization** always return **JSON**; state is in the body `state` field, result in `result`.
- **Voice conversion, noise removal, audio infilling** return the **processed audio file as raw binary** on SUCCESS (not JSON). Distinguish via the `task-state` response header (or `content-type: audio/*`). A `log-id` header carries the log id for rating.

```python
import time

def poll_json(base_url, headers, status_path, timeout=300, interval=3):
    """For JSON-returning status endpoints (ASR / forced alignment / diarization)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = requests.get(f"{base_url}/{status_path}", headers=headers).json()
        if data.get("state") in ("SUCCESS", "FAILURE"):
            return data
        time.sleep(interval)
    raise TimeoutError(status_path)

def poll_binary(base_url, headers, status_path, out_path, timeout=300, interval=5):
    """For binary-returning status endpoints (voice conv / noise removal / infilling)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{base_url}/{status_path}", headers=headers)
        if resp.headers.get("task-state") == "SUCCESS":
            open(out_path, "wb").write(resp.content)
            return resp.headers.get("log-id")
        if resp.headers.get("content-type", "").startswith("application/json"):
            d = resp.json()
            if d.get("state") == "FAILURE":
                raise RuntimeError((d.get("error") or {}).get("message", d.get("error")))
        time.sleep(interval)
    raise TimeoutError(status_path)
```

## Versioning: no-prefix / v1 vs v2

The same handlers are mounted three ways:
- **No-prefix** (e.g. `/asr/transcribe`) — the **frozen release contract** (== v1). This is what the examples below use and what existing clients call.
- **`/v1/...`** — identical to no-prefix, explicit.
- **`/v2/...`** — the **live, evolving** surface, with RESTful plural-noun kebab-case names (e.g. `/v2/transcriptions`, `/v2/voice-conversions`). Submit and poll share the resource path: `POST /v2/transcriptions` → `GET /v2/transcriptions/{task_id}`.

Rough v1 → v2 name map: `/asr/transcribe`→`/v2/transcriptions`, `/asr/phonetic`→`/v2/phonetic-transcriptions`, `/asr/languages`→`/v2/transcriptions/languages`, `/asr/recommend-language`→`/v2/language-recommendations`, `/asr/admin/models`→`/v2/asr/models`, `/voice_conversion`→`/v2/voice-conversions`, `/noise_removal`→`/v2/noise-removals`, `/audio_infilling`→`/v2/audio-infillings`, `/force_alignment`→`/v2/forced-alignments`, `/force_alignment_dataset`→`/v2/forced-alignment-datasets`, `/speaker_diarization_dataset`→`/v2/speaker-diarizations`.

**Use no-prefix for stable scripting; use `/v2` for new work.** Check `/openapi.json` when a v2 param/shape is uncertain — v2 can change.

## Endpoints (no-prefix / v1 contract)

| Service | Submit | Poll | Returns |
|---|---|---|---|
| Transcribe (ASR) | `POST /asr/transcribe` | `GET /asr/transcribe/{id}` | JSON |
| Batch transcribe | `POST /asr/batch` | `GET /asr/batch/{id}` | JSON |
| Phonetic / IPA | `POST /asr/phonetic` | `GET /asr/phonetic/{id}` | JSON |
| Recommend language | `POST /asr/recommend-language` | `GET /asr/recommend-language/{id}` | JSON (may return immediately on exact match) |
| List ASR languages | `GET /asr/languages` | — | JSON (no auth) |
| Submit rating | `POST /asr/rating` | — | JSON |
| Admin: models | `GET/POST/PUT/DELETE /asr/admin/models[/{id}]` | — | JSON (admin only) |
| Forced alignment | `POST /force_alignment` | `GET /force_alignment_status/{id}` | JSON |
| Forced align (HF dataset) | `POST /force_alignment_dataset` | `GET /force_alignment_status/{id}` | JSON |
| Voice conversion | `POST /voice_conversion` | `GET /voice_conversion_status/{id}` | **binary** |
| Noise removal | `POST /noise_removal` | `GET /noise_removal_status/{id}` | **binary** |
| Audio infilling | `POST /audio_infilling` | `GET /audio_infilling_status/{id}` | **binary** |
| Speaker diarization | `POST /speaker_diarization_dataset` | `GET /speaker_diarization_status/{id}` | JSON |
| Health | `GET /health` | — | JSON (no auth) |

Audio input is generally either a multipart `file` upload **or** an `s3_file_path` query/form param (`s3://bucket/key`). `s3_upload` (default `true`) controls whether the result is stored to S3; pass `false` to get the result inline.

## Quick recipes

### Transcribe (ASR)

```python
# method: w2v-bert (default) | whisper | mms | omnilingual | phonetic
with open("audio.mp3", "rb") as f:
    r = requests.post(f"{base_url}/asr/transcribe", headers=headers,
                      files={"file": ("audio.mp3", f, "audio/mpeg")},
                      params={"language_iso": "spa", "method": "mms", "s3_upload": False})
task_id = r.json()["task_id"]
data = poll_json(base_url, headers, f"asr/transcribe/{task_id}")
print(data["result"])   # {"transcription": {"transcription": "...", "method": "mms"}, "log_id": ...}
```

Key `POST /asr/transcribe` params: `language_iso` (required, ISO 639-3, e.g. `bcc_Latn`), `method`, `romanize` (default false), `timestamp_level` (`chunk`|`word`|`character`), `best_quality` (w2v-bert: run all active models). `GET /asr/languages` lists ~1600 languages (`{"languages": [...], "entries": [...]}`); filter with `?language_iso=bcc_Latn`.

### Word-level timestamps (needed for infilling text edits)

`POST /asr/phonetic` with `language_iso` + `timestamp_level="word"`; the result's `words` array (`[{"word","start","end"}, ...]`) feeds `word_times` for audio infilling.

### Forced alignment

```python
import json
with open("audio.mp3", "rb") as f:
    r = requests.post(f"{base_url}/force_alignment", headers=headers,
                      files=[("files", ("audio.mp3", f, "audio/mpeg"))],
                      data={"ref_texts": json.dumps(["En el principio"]),
                            "romanize": "false", "s3_upload": "false"})
data = poll_json(base_url, headers, f"force_alignment_status/{r.json()['task_id']}")
```

`ref_texts` is a JSON array (one text per audio file). Multiple `files` align to multiple `ref_texts` by position.

### Voice conversion (binary result)

```python
# model: freevc (default, A10G) | seed_vc (zero-shot) | playdiffusion (experimental)
with open("source.mp3","rb") as s, open("target.mp3","rb") as t:
    r = requests.post(f"{base_url}/voice_conversion", headers=headers,
        files=[("source_file",("source.mp3",s,"audio/mpeg")),
               ("target_file",("target.mp3",t,"audio/mpeg"))],
        params={"model": "freevc", "s3_upload": False})
poll_binary(base_url, headers, f"voice_conversion_status/{r.json()['task_id']}", "converted.mp3")
```

Provide **both** uploads (`source_file`+`target_file`) **or** both S3 paths (`s3_source_file_path`+`s3_target_file_path`) — mixing returns 400.

### Noise removal (binary result)

```python
# method: mpnet (default, general) | sam (text-prompted isolation; supports prompt=, quality=standard|high)
with open("noisy.wav","rb") as f:
    r = requests.post(f"{base_url}/noise_removal", headers=headers,
        files={"file": ("noisy.wav", f, "audio/wav")},
        params={"method": "mpnet", "s3_upload": False})
poll_binary(base_url, headers, f"noise_removal_status/{r.json()['task_id']}", "denoised.wav")
```

### Audio infilling (binary result)

Two modes — **splice audio clips** via `replacements`, or **change spoken words** via `modified_text`:

```python
# Splice: replacements = JSON array of {start, end, audio_filename|audio_s3_path|audio_base64}
data = {"s3_file_path": "s3://bucket/source.wav", "s3_upload": False,
        "replacements": json.dumps([{"start": 1.15, "end": 1.68, "audio_s3_path": "s3://bucket/clip.mp3"}])}
r = requests.post(f"{base_url}/audio_infilling", headers=headers, data=data)

# Text edit: send the FULL target transcript in modified_text + the original input_text + word_times.
# word_times is REQUIRED for text edits (get it from /asr/phonetic, timestamp_level="word").
data = {"s3_file_path": "s3://bucket/source.wav", "input_text": "...original...",
        "modified_text": "...full target...", "word_times": json.dumps(word_times), "s3_upload": False}
r = requests.post(f"{base_url}/audio_infilling", headers=headers, data=data)
```

There is **no** per-replacement `text` field — to change words, use `modified_text`. A text edit without `word_times` fails with a Modal "zero-length tensor" error (that's the missing timings, not a bad audio file).

## Gotchas

- **Binary vs JSON status responses** — voice conversion / noise removal / audio infilling return raw audio on SUCCESS; gate on the `task-state` header, not `.json()`.
- Tokens expire (~30 min) → re-auth on 401. `/token` is rate-limited (5/min/IP).
- `s3_upload=False` gives you the result inline (binary or in `result`) instead of an S3 URL — handy for quick tests.
- `language_iso` for ASR is ISO 639-3, optionally with script suffix (`bcc_Latn`); wrong/unsupported codes are a common failure. Use `/asr/recommend-language` to find the closest supported language.
- Diarization and `force_alignment_dataset` operate on **Hugging Face datasets**, not single uploads.
- `/openapi.json` is authoritative — consult it (especially for `/v2`) before assuming a param name or response shape.
