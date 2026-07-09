---
name: alpha2-api
description: Call the Alpha2 (multilingualai.com) Text Collection API to machine-translate text and generate text-to-speech audio for low-resource languages. Use when you need to translate a batch of lines between languages, synthesize speech from text, discover available translation/TTS models and speakers, or drive any Alpha2 v2 endpoint. Covers auth, the create-collection → run → poll pattern, and result shapes.
---

# Alpha2 API

The Alpha2 API (a.k.a. the "Text Collection API") powers translation and text-to-speech for the multilingualai / Acts2 platform. Both features share the same core object — a **text collection** (a named list of source lines in one language) — and both follow the same async pattern: create a collection, kick off a job, then poll for results.

## Invocation

This skill is user-invocable. Users can say:
- `/alpha2-api` — show usage help
- `/alpha2-api translate <src_iso> <trg_iso> <text>` — translate text and poll to completion
- `/alpha2-api tts <language_iso> <text>` — synthesize speech and return audio URLs
- `/alpha2-api models <src_iso> <trg_iso>` — list translation models for a language pair
- `/alpha2-api tts-models <language_iso>` — list TTS models + speakers for a language

## API Details

- **Base URL**: `https://alpha2.multilingualai.com/api`
- **Docs (Swagger UI)**: https://alpha2.multilingualai.com/api/docs
- **OpenAPI spec**: https://alpha2.multilingualai.com/api/openapi.json
- **Current version**: all endpoints below are under the `/v2` prefix. A legacy `/v1` (and unprefixed) API also exists — prefer `/v2`.

**Gotcha**: FastAPI is mounted under Django at `/api`, so every path is `/api/v2/...` (e.g. `https://alpha2.multilingualai.com/api/v2/text_collections`). Hitting `/v2/...` without the `/api` prefix returns Django 404s.

There is also a production host, `acts2.multilingualai.com`, with the same API shape. This skill targets **alpha2** (the staging/dev droplet). Swap the host if you mean production.

## Credentials

Auth is a single **API key sent in the `api_key` request header** (NOT `Authorization: Bearer`). Generate a key from your account settings in the web app; each key is tied to a user, and all usage is billed to that user.

Set it before invoking the skill:

```bash
export ALPHA2_API_KEY="your_api_key_here"
```

Ask the user for their key if it isn't already set. Never commit keys.

```bash
# Sanity check: 401 with no key, 200 with a valid key
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://alpha2.multilingualai.com/api/v2/text_collections" \
  -H "api_key: ${ALPHA2_API_KEY}"
```

## Key Endpoints

All endpoints require the `api_key: $ALPHA2_API_KEY` header. `iso` means a language ISO code (e.g. `en`, `swh`).

| Endpoint | Description |
|---|---|
| `GET  /api/v2/text_collections` | List your text collections |
| `POST /api/v2/text_collections` | Create a collection (body: `name`, `language`, and `text` or `texts`) |
| `GET  /api/v2/text_collections/{id}/texts` | List texts in a collection; `?include_translations=true` for nested translations |
| `POST /api/v2/text_collections/{id}/translate` | Translate a collection (query: `target_language`, optional `model_id`) → returns a NEW target collection |
| `DELETE /api/v2/text_collection/{id}` | Soft-delete a collection |
| `GET  /api/v2/translation_models` | List translation models; filter with `?src=<iso>&trg=<iso>` |
| `GET  /api/v2/tts_languages` | Languages that have an active TTS model |
| `GET  /api/v2/tts_models` | List TTS models; `?language=<iso>` also returns that language's speakers |
| `GET  /api/v2/tts_speakers` | List speaker profiles; requires `?model_id=` or `?language=` |
| `POST /api/v2/text_collections/{id}/tts` | Run TTS on a collection (query: optional `model_id`, `speaker_id`) → returns a TTS collection |
| `GET  /api/v2/tts_collections/{tts_id}/tts_results` | Poll TTS results by TTS collection id (paginated) |
| `GET  /api/v2/text_collections/{id}/tts_results` | Poll TTS results by source collection (query: `model_id`, optional `speaker_id`) |

**Status values** (for both `translation_status` on texts and `status` on audios): `pending`, `running`, `complete`, `failed`, `retry`. A collection also exposes running counts (`total`/`running`/`complete`/`pending`/`failed`).

## Instructions

Both flows start by creating a source collection.

### Create a text collection

`text` is split on newlines into one text per line; alternatively pass `texts` as an explicit JSON array. Exactly one of the two.

```bash
COLLECTION=$(curl -s -X POST "https://alpha2.multilingualai.com/api/v2/text_collections" \
  -H "api_key: ${ALPHA2_API_KEY}" -H "Content-Type: application/json" \
  -d '{"name": "demo", "language": "en", "texts": ["Hello, world.", "How are you?"]}')
COLLECTION_ID=$(echo "$COLLECTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

### Translation flow

1. (Optional) Find a model id — otherwise the best model for the language pair is auto-selected:

```bash
curl -s "https://alpha2.multilingualai.com/api/v2/translation_models?src=en&trg=swh" \
  -H "api_key: ${ALPHA2_API_KEY}"
```

2. Kick off the translation. This creates and returns a **new target collection** (its texts start out `pending`). Optional JSON body: `glossary` (`{"source_word": "target_word"}`, only for models where `supports_glossary` is true) and `prefix_overrides` (SFM collections only).

```bash
TARGET=$(curl -s -X POST \
  "https://alpha2.multilingualai.com/api/v2/text_collections/${COLLECTION_ID}/translate?target_language=swh" \
  -H "api_key: ${ALPHA2_API_KEY}")
TARGET_ID=$(echo "$TARGET" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

3. Poll for results. Translation runs on a background Celery worker, so results are not immediate. Query the **source** collection's texts with `include_translations=true` (filter by `target_language` to isolate this run); each source text carries a nested `translations` list with `text` and `translation_status`:

```bash
curl -s "https://alpha2.multilingualai.com/api/v2/text_collections/${COLLECTION_ID}/texts?include_translations=true&target_language=swh" \
  -H "api_key: ${ALPHA2_API_KEY}"
```

Poll every few seconds until every nested translation's `translation_status` is `complete` (or `failed`). Small batches finish in seconds; large ones (thousands of lines) take minutes.

### Text-to-speech flow

1. Discover what's available for the language (models bundle their speakers when `?language=` is passed):

```bash
curl -s "https://alpha2.multilingualai.com/api/v2/tts_models?language=swh" \
  -H "api_key: ${ALPHA2_API_KEY}"
# or list speakers directly:
curl -s "https://alpha2.multilingualai.com/api/v2/tts_speakers?language=swh" \
  -H "api_key: ${ALPHA2_API_KEY}"
```

2. Run TTS on a collection. `model_id` defaults to the best model for the language; `speaker_id` (a `SpeakerProfile` id from the calls above) is optional. Returns a **TTS collection** with an `id`:

```bash
TTS=$(curl -s -X POST \
  "https://alpha2.multilingualai.com/api/v2/text_collections/${COLLECTION_ID}/tts?model_id=12&speaker_id=3" \
  -H "api_key: ${ALPHA2_API_KEY}")
TTS_ID=$(echo "$TTS" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

3. Poll for audio. Results are paginated under `audios.results[]`, each with `source_text`, `status`, and `audio_url` (an S3 URL, populated once `status` is `complete`):

```bash
curl -s "https://alpha2.multilingualai.com/api/v2/tts_collections/${TTS_ID}/tts_results?page=1&page_size=100" \
  -H "api_key: ${ALPHA2_API_KEY}"
```

Poll until each audio's `status` is `complete`. Download `audio_url` directly with `curl -o` (the S3 URLs are pre-signed and time-limited — fetch promptly).

### Saving data

Save fetched JSON / audio to `/tmp/` or another scratch location by default, not into project repos, unless the user explicitly asks to persist it.

## Notes

- 401 `{"detail": "No API Key provided"}` → the `api_key` header is missing; `{"detail": "Invalid API Key"}` → the key doesn't match a user.
- The API is rate-limited (default 10,000 requests/day per IP). Keep polling intervals reasonable (e.g. every 3–5s), not a tight loop.
- `translate` and `tts` return immediately with the new (target / TTS) collection — the actual work happens asynchronously. Always poll; don't assume the first response contains finished results.
- If a model or speaker can't be auto-selected you'll get a 400 ("No translation model found…" / "No text to speech model found…") — list the models first and pass an explicit `model_id`.
- The OpenAPI spec at `/api/openapi.json` is the authoritative reference for every endpoint, parameter, and response schema. Fetch it if a call behaves unexpectedly.
