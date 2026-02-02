# SIL Shared Skills

AI coding skills developed by and for [Claude Code](https://claude.ai/code), but should be compatible with other AI coding agents. These skills cover common Bible NLP tasks used by the SIL AI Capability Team and others.

## Available Skills

| Skill | Invocation | Description |
|-------|------------|-------------|
| vref-format | `/vref-format` | VREF format documentation and usage |
| usfm-to-vref | `/usfm-to-vref` | Convert USFM/Paratext to vref-aligned text |
| vref-to-usfm | `/vref-to-usfm` | Convert vref-aligned text to USFM/SFM files |
| modal-dev | `/modal-dev` | Modal serverless development guidelines |

## Installation

### Option A: Symlink Skills (Recommended)

```bash
# Clone this repo
git clone https://github.com/sil-ai/shared-skills.git ~/sil-shared-skills

# Create skills directory if needed
mkdir -p ~/.claude/skills

# Symlink the skills you want
ln -s ~/sil-shared-skills/skills/vref-format ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/usfm-to-vref ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/vref-to-usfm ~/.claude/skills/
ln -s ~/sil-shared-skills/skills/modal-dev ~/.claude/skills/
```

### Option B: Copy Skills

```bash
cp -r ~/sil-shared-skills/skills/* ~/.claude/skills/
```

## Updating

If using symlinks, pull to get updates:

```bash
git -C ~/sil-shared-skills pull
```

## Usage

Invoke skills by typing `/skillname` in Claude Code:
- `/vref-format` - Get VREF format documentation
- `/usfm-to-vref` - Get USFM conversion guidance
- `/vref-to-usfm` - Convert vref text back to USFM
- `/modal-dev` - Get Modal development guidelines

## Contributing

To add a new skill:
1. Create `skills/<skill-name>/SKILL.md` with YAML front matter
2. Add skill to the table in this README
3. Commit and push
