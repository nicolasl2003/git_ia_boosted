# git-booster

AI-powered Git wrapper using **local Ollama** (no API key required). Supercharge your git workflow with automatic commit messages, `.gitignore` generation, merge conflict resolution, and code review.

## Features

| Command       | Description                                                  |
|---------------|--------------------------------------------------------------|
| `gai config`  | Interactive setup: provider, Ollama install, model selection |
| `gai add`     | `git add .` + AI-generated/updated `.gitignore`              |
| `gai status`  | `git status` + AI summary of the repo state                  |
| `gai commit`  | Generate commit message, validate/modify, commit + push      |
| `gai resolve` | Detect and resolve merge conflicts with AI                   |
| `gai review`  | AI code review of staged changes before committing           |

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally (`ollama serve`)
- A pulled model (see `gai config`)

## Installation

```bash
# 1. Clone the project
git clone <repo> && cd git_booster

# 2. Create virtualenv and install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. (Recommended) Use the wrapper script for auto env activation
# Add to ~/.zshrc:
alias gai="/path/to/git_booster/gai"

# 4. Configure provider and model
gai config
```

## Quick start

```bash
# First time — configure Ollama + model
gai config

# Inside any git repo:
gai add          # stage everything + generate .gitignore
gai status       # enriched status with AI summary
gai review       # review staged changes before committing
gai commit       # auto-generate commit message → validate → commit → push
gai resolve      # resolve merge conflicts
```

## `gai commit` workflow

```
A.I is processing...
┌─ Generated commit message ──────────────────────┐
│ feat(ai): replace Claude references with Ollama  │
└──────────────────────────────────────────────────┘
What do you want to do? [commit/edit/regenerate/abort] (commit):
  commit      → commit as-is
  edit        → open in $EDITOR
  regenerate  → give feedback, AI rewrites
  abort       → cancel

Push to remote? [y/N]
```

## Configuration

Settings are stored in `~/.config/git-booster/config.env`.  
Run `gai config` to update them interactively.

| Variable          | Default                    | Description                  |
|-------------------|----------------------------|------------------------------|
| `OLLAMA_HOST`     | `http://localhost:11434`   | Ollama server URL            |
| `GAI_MODEL`       | `llama3.2`                 | Model to use                 |
| `GAI_PROVIDER`    | `ollama`                   | AI provider                  |
| `ANTHROPIC_API_KEY` | —                        | Only if using Anthropic      |
| `OPENAI_API_KEY`  | —                          | Only if using OpenAI         |

### Recommended model for GTX 1050 Ti (4GB VRAM)

```bash
ollama pull qwen2.5-coder:3b   # ~2GB VRAM, optimised for code
export GAI_MODEL=qwen2.5-coder:3b
```

## Project structure

```
git_booster/
├── gai                         # Shell wrapper (auto-activates .venv + .env)
├── git_booster/
│   ├── cli.py                  # CLI entry point (click)
│   ├── core/
│   │   └── git.py              # All git subprocess calls
│   ├── ai/
│   │   ├── client.py           # Ollama HTTP client
│   │   └── prompts.py          # All prompt templates
│   └── commands/
│       ├── config.py           # gai config — interactive setup
│       ├── add.py              # gai add
│       ├── status.py           # gai status
│       ├── commit.py           # gai commit
│       ├── resolve.py          # gai resolve
│       └── review.py           # gai review
├── pyproject.toml
└── .env.example
```
