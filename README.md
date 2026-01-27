# SIL Shared Skills

Shared documentation and knowledge for Claude Code, available across all your projects.

## Setup

1. Clone this repo to your home directory:
   ```bash
   git clone https://github.com/sil-ai/shared-skills.git ~/sil-shared-skills
   ```

2. Add to your Claude Code settings. Edit `~/.claude/settings.json`:
   ```json
   {
     "includeColocatedInstructions": ["~/sil-shared-skills"]
   }
   ```

   If the file doesn't exist, create it with the content above.

3. Restart Claude Code. The shared knowledge is now available in all your projects.

## Updating

Pull the latest changes periodically:
```bash
git -C ~/sil-shared-skills pull
```

## What's Included

| File | Description |
|------|-------------|
| [vref.md](vref.md) | VREF format documentation - line-based verse alignment system |
| [USFMConversion.md](USFMConversion.md) | Converting USFM/Paratext projects to VREF format |

## How It Works

- `CLAUDE.md` is loaded into Claude's context automatically (minimal token usage)
- The detailed documentation files are read on-demand when relevant to your task
- Claude can reference this knowledge in any project on your machine

## Contributing

To add new documentation:

1. Create a new `.md` file with your documentation
2. Add a reference to it in `CLAUDE.md`
3. Commit and push

Teammates will get the updates on their next `git pull`.
