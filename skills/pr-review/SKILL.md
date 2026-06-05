# PR Review

Create a PR with agent-based code review, apply fixes, and re-review until clean.

## Invocation

This skill is user-invocable. Users can say:
- `/pr-review` - Full cycle: create PR, review, fix, re-review
- `/pr-review review` - Review only (PR already exists on current branch)
- `/pr-review fix` - Apply fixes from a previous review without re-creating the PR

## Instructions

### Step 1: Understand the Changes

1. Run `git diff main...HEAD` (or the appropriate base branch) to see all changes
2. Run `git log main..HEAD --oneline` to see all commits being included
3. Run `git status` to check for uncommitted changes — if there are any, ask the user if they want to commit first

### Step 1.5: Run Linting

Before creating the PR, run the project's linter to catch issues early:
- Look for a linting command in `Makefile`, `package.json` scripts, `pyproject.toml`, or similar
- Common linters: `ruff check`, `flake8`, `eslint`, `mypy`, `npm run lint`
- If linting fails, fix the issues, commit, and re-run until clean
- If no linter is configured, skip this step

### Step 2: Create the PR (skip if `review` or `fix` subcommand)

1. Determine the base branch (usually `main`)
2. **Detect related GitHub issues** to auto-close on merge:
   - Check the branch name for issue numbers (e.g., `fix/123-some-bug`, `feature/gh-45`)
   - Check commit messages for issue references (e.g., `#123`, `fixes #123`)
   - Check the conversation context for issue numbers or links the user mentioned
   - Run `gh issue list --state open --limit 20` to cross-reference if the branch/commits hint at an issue
   - If an issue is found, include `Fixes #N` (or `Fixes owner/repo#N` for cross-repo) in the PR body
3. Push the current branch to origin with `git push -u origin HEAD`
4. Create the PR with `gh pr create`:
   - Title: concise, under 70 chars
   - Body: summary bullets, `Fixes #N` if a related issue was found, test plan, and the Claude Code footer
   - Use a HEREDOC for the body to preserve formatting

### Step 3: Run Agent Reviews

Launch review agents in parallel using the Agent tool. Decide which review concerns are relevant based on the nature of the PR — use as many or as few agents as make sense. Possible review angles include:

- **Bugs & logic** — off-by-one errors, incorrect logic, missing error handling, parameter threading through intermediate layers
- **Security** — injection, XSS, auth issues, secrets exposure
- **Style & consistency** — codebase patterns, unnecessary defensive code, dead code, unused imports, naming
- **Tests & integration** — missing tests, broken existing tests, missing migrations, backward compatibility
- **Performance** — N+1 queries, unnecessary allocations, blocking calls in async code
- **API design** — endpoint naming, response shapes, breaking changes

For small PRs, a single comprehensive agent may be enough. For large PRs touching multiple concerns, split into parallel agents for speed.

**Specialist agents** — prefer these over a generic reviewer when the PR touches their domain, and run them in parallel with the general angles above:
- **`fastapi-expert`** — any PR touching FastAPI routers, path operations, dependencies, Pydantic request/response models, async DB sessions, background tasks, middleware/lifespan, or the uvicorn/gunicorn server config. Catches event-loop blocking, dependency-lifecycle bugs, and API-contract regressions.
- **`django-expert`** — any PR touching Django models, migrations, querysets, or DRF serializers/viewsets (see also the migration note below).

Each agent should output a numbered list of findings with severity (critical / warning / nit).

### Step 4: Consolidate Findings

Combine all agent findings into a single list, deduplicated and sorted by severity:
1. **Critical** — bugs, security issues, broken functionality (must fix)
2. **Warning** — missing tests, inconsistencies, potential issues (should fix)
3. **Nit** — style, naming, minor improvements (optional)

Present the consolidated findings to the user and ask if they want to:
- **Fix all** — auto-fix everything (critical + warning + nit)
- **Fix important** — auto-fix critical + warning only
- **Fix critical only** — just the must-fix items
- **Skip** — don't fix anything, just leave the review as a comment

### Step 5: Apply Fixes

For each finding the user chose to fix:
1. Make the code change
2. Run tests if available (`pytest`, `npm test`, etc.)
3. If tests fail, diagnose and fix before moving on

After all fixes are applied:
1. Stage and commit the fixes with a message like "Apply PR review feedback: fix [summary]"
2. Push to the remote branch

### Step 6: Re-Review (Verification Pass)

Run a single verification agent to confirm:
- All critical findings have been addressed
- No new issues were introduced by the fixes
- Tests still pass

If new issues are found, report them to the user and offer to fix.

### Step 7: Request Copilot Review

After our own review cycle is clean, request a GitHub Copilot code review.

**IMPORTANT:** Do NOT use `gh pr edit --add-reviewer` — it fails on repos with Projects Classic enabled (GraphQL error). Use the REST API instead:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers --method POST -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
```

Note: The Copilot reviewer username is `copilot-pull-request-reviewer[bot]`. Shorter names like `copilot` or `copilot[bot]` silently succeed but do NOT actually tag Copilot.

Then poll for Copilot's review in a single bash loop (so the user only needs to approve one command):

```bash
for i in $(seq 1 15); do
  echo "Poll attempt $i at $(date +%H:%M:%S)"
  count=$(gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '[.[] | select(.user.login == "copilot-pull-request-reviewer[bot]")] | length')
  echo "Reviews found: $count"
  if [ "$count" -gt 0 ]; then
    echo "Copilot review found!"
    gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | select(.user.login == "copilot-pull-request-reviewer[bot]") | {id, state, body}'
    break
  fi
  if [ "$i" -eq 15 ]; then
    echo "Timed out after 15 attempts"
    break
  fi
  sleep 60
done
```

Use a timeout of 600000ms (10 minutes) on the bash call. If the loop times out after 15 attempts, tell the user Copilot review hasn't arrived yet and offer to continue waiting or skip.

Once a review is found, fetch inline comments using the review ID:
```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}/comments --jq '.[] | {path, line, body}'
```

**IMPORTANT:** Copilot attaches inline comments to the review object, NOT as top-level PR comments. Do NOT rely solely on `pulls/{pr_number}/comments` — it may return empty even when Copilot left inline feedback.

### Step 8: Address Copilot Findings

For each Copilot comment:
1. Read the comment and the surrounding code context
2. Determine if the suggestion is valid (sometimes Copilot flags things that are intentional)
3. Present Copilot's findings to the user with your assessment of each — recommend accept/reject
4. Apply the accepted fixes, commit, and push

### Step 9: Check CI/CD and Fix Failing Tests

After all code-review fixes are pushed, verify GitHub's CI/CD checks pass. The PR must reach a green state before this skill is considered done.

1. Poll for check completion (checks may not register immediately after push):

```bash
for i in $(seq 1 20); do
  echo "Poll attempt $i at $(date +%H:%M:%S)"
  status=$(gh pr checks {pr_number} --json state,name,conclusion 2>/dev/null)
  if [ -z "$status" ] || [ "$status" = "[]" ]; then
    echo "No checks reported yet"
  else
    pending=$(echo "$status" | jq '[.[] | select(.state == "PENDING" or .state == "IN_PROGRESS" or .state == "QUEUED")] | length')
    echo "$status" | jq -r '.[] | "\(.name): \(.state) \(.conclusion // "")"'
    if [ "$pending" = "0" ]; then
      echo "All checks complete"
      break
    fi
  fi
  if [ "$i" -eq 20 ]; then
    echo "Timed out waiting for checks"
    break
  fi
  sleep 30
done
```

Use a timeout of 600000ms (10 minutes) on the bash call.

2. Identify failures with `gh pr checks {pr_number}` and fetch logs for failing jobs:

```bash
gh run list --branch $(git branch --show-current) --limit 5
gh run view {run_id} --log-failed
```

3. **Fix each failing check**:
   - Read the failure log to find the root cause (failing test, lint error, type error, build failure)
   - Read the relevant source/test files to understand the issue
   - Apply a minimal fix — do not paper over real failures by deleting/skipping tests unless the test itself is genuinely wrong (and confirm with the user before doing so)
   - Run the failing test locally if possible (`pytest path::test_name`, `npm test -- --testPathPattern=...`) to verify the fix
   - Commit with a message like "Fix CI: [specific failure summary]"
   - Push and re-poll CI

4. Repeat until all checks pass. If a check is clearly an infra/flaky issue (not a real failure of the PR's code), note it explicitly and ask the user before proceeding.

5. Confirm final state with `gh pr checks {pr_number}` — every required check should show `pass`/`success`. The PR is not considered done until CI is green.

### Step 10: Final Summary

Output a summary:
```
## PR Review Complete

**PR:** [link]

### Agent Review
**Findings:** X critical, Y warnings, Z nits
**Fixed:** N items
**Remaining:** M items (nits skipped by user choice)

### Copilot Review
**Comments:** X total
**Accepted & fixed:** N
**Declined:** M (with reasons)

### CI/CD
**Checks:** all passing / X failed → fixed
**Final state:** green

Ready to merge: [Yes/No — with reason if No]
```

## Notes

- If the user says `/pr-review` with no PR and no new commits beyond main, warn them there's nothing to review
- If `gh` CLI is not authenticated, tell the user to run `gh auth login`
- The review agents should read actual file contents, not just the diff — context matters for catching bugs
- For Django projects, always check that migrations are included if models changed
- For Modal projects, check that deployment config is consistent with the code changes
- Keep review output concise — developers don't want to read essays, they want actionable items
