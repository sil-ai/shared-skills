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

## Available Agents

Agents are specialized reviewers that Claude Code can launch as subagents via the Task tool. They run automatically when relevant tasks are detected.

| Agent | Description |
|-------|-------------|
| architect | System design decisions, API boundaries, data models, scalability tradeoffs |
| code-reviewer | Code quality, readability, maintainability, correctness, best practices |
| security-auditor | Security vulnerabilities, auth flows, dependency risks, threat modeling |
| qa-strategist | Test strategies, edge cases, coverage, regression risks |
| devops-engineer | Docker, CI/CD, deployment, infrastructure, Modal configs |
| ml-engineer | ML pipelines, model selection, training configs, evaluation (NLP/speech/low-resource focus) |
| devils-advocate | Challenge assumptions, stress-test plans, surface hidden risks |
| ux-reviewer | UI/UX review for intuitiveness, visual consistency, accessibility, polish |

## Installation

### Option A: Symlink (Recommended)

```bash
# Clone this repo
git clone https://github.com/sil-ai/shared-skills.git ~/sil-shared-skills

# Create directories if needed
mkdir -p ~/.claude/skills ~/.claude/agents

# Symlink skills
ln -s ~/sil-shared-skills/skills/vref-format ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/usfm-to-vref ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/vref-to-usfm ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/modal-dev ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/aqua-api ~/.claude/skills/

# Symlink agents
for agent in ~/sil-shared-skills/agents/*.md; do
  ln -sf "$agent" ~/.claude/agents/
done
```

### Option B: Copy

```bash
cp -r ~/sil-shared-skills/skills/* ~/.claude/skills/
cp ~/sil-shared-skills/agents/*.md ~/.claude/agents/
```

## Updating

If using symlinks, pull to get updates:

```bash
git -C ~/sil-shared-skills pull
```

## Usage

### Skills

Invoke skills by typing `/skillname` in Claude Code:
- `/vref-format` - Get VREF format documentation
- `/usfm-to-vref` - Get USFM conversion guidance
- `/vref-to-usfm` - Convert vref text back to USFM
- `/modal-dev` - Get Modal development guidelines
- `/aqua-api` - Access Bible text/revisions via the SIL Aqua API

### Agents

Agents are used automatically by Claude Code when it detects relevant tasks. You can also request them explicitly, e.g.:
- "Run the code reviewer on my changes"
- "Have the architect evaluate this design"
- "Get the security auditor to check this auth flow"

## Contributing

To add a new skill:
1. Create `skills/<skill-name>/SKILL.md` with YAML front matter
2. Add skill to the table in this README
3. Commit and push

To add a new agent:
1. Create `agents/<agent-name>.md` with YAML front matter (`name`, `description`, `model`, `memory`)
2. Add agent to the table in this README
3. Commit and push
