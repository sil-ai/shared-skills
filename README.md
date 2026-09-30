# SIL Shared Skills & Agents

AI coding skills and agents developed by and for [Claude Code](https://claude.ai/code), but should be compatible with other AI coding agents. These cover common Bible NLP tasks and software engineering review workflows used by the SIL AI Capability Team and others.

## Available Skills

| Skill | Invocation | Description |
|-------|------------|-------------|
| vref-format | `/vref-format` | VREF format documentation and usage |
| usfm-to-vref | `/usfm-to-vref` | Convert USFM/Paratext to vref-aligned text |
| vref-to-usfm | `/vref-to-usfm` | Convert vref-aligned text to USFM/SFM files |
| modal-dev | `/modal-dev` | Modal serverless development guidelines |
| aqua-api | `/aqua-api` | Access Bible text/revisions via the SIL Aqua API |
| pr-review | `/pr-review` | Agent-based PR review cycle: create PR, review, fix, re-review, drive CI to green |
| md-to-sil-docx | `/md-to-sil-docx` | Convert Markdown into a SIL-branded .docx (title block, headings, lists, tables) |
| loki-logs | `/loki-logs` | Query the multilingualai Grafana Loki logs for any project/environment (errors, traces, recent activity) |
| aero-api | `/aero-api` | Call the SIL AERO API for AI audio processing (ASR, forced alignment, voice conversion, noise removal, audio infilling, diarization) |
| alpha2-api | `/alpha2-api` | Machine-translate text and generate TTS audio via the Alpha2 (multilingualai) Text Collection API |
| clearml-jobs | `/clearml-jobs` | Submit training jobs to the SIL ClearML server (queues, launcher/worker split, monitoring) |
| decision-models | `/decision-models` | Fast, cheap System One decision models (Jev etc.) via OpenRouter: yes/no, choice and score judgments, question design, usage patterns |

## Available Agents

Agents are specialized reviewers that Claude Code can launch as subagents via the Task tool. They run automatically when relevant tasks are detected.

| Agent | Description |
|-------|-------------|
| architect | System design decisions, API boundaries, data models, scalability tradeoffs |
| code-reviewer | Code quality, readability, maintainability, correctness, best practices |
| django-expert | Django review: migration safety, ORM correctness, DRF, DB/deployment interactions |
| fastapi-expert | FastAPI review: async/event-loop correctness, dependency injection, Pydantic, async DB sessions |
| security-auditor | Security vulnerabilities, auth flows, dependency risks, threat modeling |
| qa-strategist | Test strategies, edge cases, coverage, regression risks |
| devops-engineer | Docker, CI/CD, deployment, infrastructure, Modal configs |
| ml-engineer | ML pipelines, model selection, training configs, evaluation (NLP/speech/low-resource focus) |
| devils-advocate | Challenge assumptions, stress-test plans, surface hidden risks |
| ux-reviewer | UI/UX review for intuitiveness, visual consistency, accessibility, polish |

## Installation

### Option A: `npx skills` (Recommended)

Install with the [Skills CLI](https://skills.sh/). It works for Claude Code, Codex, Cursor and other agents, and needs no clone:

```bash
# Pick skills interactively
npx skills add sil-ai/shared-skills

# Or install specific skills at user level
npx skills add sil-ai/shared-skills -g -s decision-models -s aero-api

# See what's available
npx skills add sil-ai/shared-skills --list
```

Update later with `npx skills update`.

The CLI installs skills only. For agents, use Option B.

### Option B: Clone and symlink (contributors, and agents)

```bash
# Clone this repo
git clone https://github.com/sil-ai/shared-skills.git ~/sil-shared-skills

# Create directories if needed
mkdir -p ~/.claude/skills ~/.claude/agents

# Symlink all skills
for skill in ~/sil-shared-skills/skills/*/; do
  ln -sfn "$skill" ~/.claude/skills/
done

# Symlink agents
for agent in ~/sil-shared-skills/agents/*.md; do
  ln -sf "$agent" ~/.claude/agents/
done
```

To pick up changes, run `git -C ~/sil-shared-skills pull`.

## Usage

### Skills

Invoke skills by typing `/skillname` in Claude Code:
- `/vref-format` - Get VREF format documentation
- `/usfm-to-vref` - Get USFM conversion guidance
- `/vref-to-usfm` - Convert vref text back to USFM
- `/modal-dev` - Get Modal development guidelines
- `/aqua-api` - Access Bible text/revisions via the SIL Aqua API
- `/pr-review` - Run the agent-based PR review cycle
- `/md-to-sil-docx` - Convert a Markdown file into a SIL-branded .docx
- `/loki-logs` - Query the multilingualai Grafana Loki logs for a project/environment
- `/aero-api` - Call the SIL AERO API for AI audio processing (ASR, alignment, voice conversion, noise removal, infilling, diarization)

### Agents

Agents are used automatically by Claude Code when it detects relevant tasks. You can also request them explicitly, e.g.:
- "Run the code reviewer on my changes"
- "Have the architect evaluate this design"
- "Get the security auditor to check this auth flow"

## Contributing

To add a new skill:
1. Create `skills/<skill-name>/SKILL.md` with YAML front matter (`name` and `description` are required; `npx skills` skips a skill without them)
2. Add skill to the table in this README
3. Commit and push

To add a new agent:
1. Create `agents/<agent-name>.md` with YAML front matter (`name`, `description`, `model`, `memory`)
2. Add agent to the table in this README
3. Commit and push
