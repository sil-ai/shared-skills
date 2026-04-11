# Aqua API

Access Bible text, revisions, and versions via the SIL Aqua API. Use this to retrieve verse data for linguistic experiments, tokenization work, translation analysis, or any task that needs Scripture text from a specific language/translation.

## Invocation

This skill is user-invocable. Users can say:
- `/aqua-api` - Show usage help
- `/aqua-api revision <id>` - Fetch all verses for a revision by ID
- `/aqua-api versions` - List available Bible versions
- `/aqua-api revisions` - List available revisions
- `/aqua-api verse <revision_id> <book> <chapter> <verse>` - Fetch a single verse

## API Details

- **Base URL**: `https://cp3by92k8p.us-east-1.awsapprunner.com`
- **Docs (Swagger UI)**: https://cp3by92k8p.us-east-1.awsapprunner.com/docs
- **OpenAPI spec**: https://cp3by92k8p.us-east-1.awsapprunner.com/openapi.json
- **Auth**: OAuth2 password flow, token endpoint at `/latest/token`

**Gotcha**: The token endpoint is `/latest/token`, NOT `/token`. The v3 routes are accessible under either `/v3/...` or `/latest/...` — prefer `/latest/`.

## Credentials

Set these environment variables before invoking the skill:

```bash
export AQUA_API_USERNAME="your_email@sil.org"
export AQUA_API_PASSWORD="your_password"
```

If you have a local `aqua-api` repo checkout, your credentials may already be in its `.env` file under `*_API_USERNAME` / `*_API_PASSWORD` — check for your own username (the env var names are per-user):

```bash
# Example: if credentials are in ~/SIL/aqua-api/.env with a MARK_ prefix:
source <(grep -E '^MARK_API_(USERNAME|PASSWORD)=' ~/SIL/aqua-api/.env | sed 's/MARK_/AQUA_/; s/^/export /')
```

Ask the user where to find their credentials if not already set.

## Authentication

```bash
TOKEN=$(curl -s -X POST "https://cp3by92k8p.us-east-1.awsapprunner.com/latest/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${AQUA_API_USERNAME}&password=${AQUA_API_PASSWORD}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

## Key Endpoints

All endpoints require `Authorization: Bearer $TOKEN` header.

| Endpoint | Description | Required params |
|---|---|---|
| `GET /latest/version` | List all accessible versions | — |
| `GET /latest/revision` | List revisions | optional `version_id` |
| `GET /latest/text` | Fetch full revision text | `revision_id`, `include_verses` |
| `GET /latest/verse` | Fetch single verse | `revision_id`, `book`, `chapter`, `verse` |
| `GET /latest/chapter` | Fetch chapter | `revision_id`, `book`, `chapter` |
| `GET /latest/book` | Fetch book | `revision_id`, `book` |
| `GET /latest/vrefs` | Fetch specific vref list | `revision_id`, optional `vrefs` |
| `GET /latest/chapters` | List available book/chapter combos | `revision_id` |
| `GET /latest/textsearch` | Search by term | `revision_id`, `term` |

**Important**: `include_verses` parameter must be one of `all`, `union`, or `intersection` (NOT `true`/`false`). Use `all` to get every verse in the revision.

## Instructions

When the user invokes this skill:

### Fetching a full revision

```bash
# Ensure credentials are loaded (see Credentials section above)

# Get token
TOKEN=$(curl -s -X POST "https://cp3by92k8p.us-east-1.awsapprunner.com/latest/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${AQUA_API_USERNAME}&password=${AQUA_API_PASSWORD}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Fetch revision text
curl -s "https://cp3by92k8p.us-east-1.awsapprunner.com/latest/text?revision_id=${REVISION_ID}&include_verses=all" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/aqua_rev_${REVISION_ID}.json
```

The response is a list of ~41,899 verse objects, each with fields: `id`, `text`, `verse_reference`, `verse_references`, `first_verse_reference`, `revision_id`, `book`, `chapter`, `verse`.

### Filtering empty verses

Many verses may have empty text (not all books translated). Filter with:

```python
import json
with open('/tmp/aqua_rev_X.json') as f:
    data = json.load(f)
non_empty = [d for d in data if d.get('text', '').strip()]
print(f"Non-empty: {len(non_empty)}/{len(data)}")
```

### Saving data

**Default behavior**: Save fetched data to `/tmp/` or another scratch location, NOT into project repos, unless the user explicitly asks to persist it. Examples and small extracts are fine to commit; bulk revision dumps are not.

## Notes

- The token expires — re-fetch if you get 401 errors
- Use `/latest/` for v3 endpoints rather than `/v3/` for consistency
- The OpenAPI spec at `/openapi.json` is the authoritative reference for all endpoints and parameters
- If an endpoint returns `{"detail": "Not Found"}`, check you're using `/latest/` prefix
- If a parameter is rejected with an enum error, check the OpenAPI spec — several params require specific string values (like `include_verses`)
