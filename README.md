# git-booster

AI-powered Git wrapper using **Claude** (Anthropic). Supercharge your git workflow with automatic commit messages, `.gitignore` generation, merge conflict resolution, and code review.

## Features

| Command | Description |
|---------|-------------|
| `gb add` | `git add .` + AI-generated/updated `.gitignore` |
| `gb status` | `git status` + AI summary of the repo state |
| `gb commit` | Generate a Conventional Commit message from staged diff |
| `gb resolve` | Detect and resolve merge conflicts with AI |
| `gb review` | AI code review of staged changes before committing |

## Installation

```bash
# 1. Clone / copy the project
cd git_booster

# 2. Create a virtualenv (recommended)
python -m venv .venv
source .venv/bin/activate

# 3. Install
pip install -e .

# 4. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Inside any git repo:

gb add          # stage everything + generate .gitignore
gb status       # enriched status with AI summary
gb review       # review staged changes before committing
gb commit       # auto-generate commit message and commit
gb resolve      # resolve merge conflicts

# Options
gb commit --yes          # skip confirmation prompt
gb commit --path /my/repo
gb --help
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `GIT_BOOSTER_MODEL` | `claude-3-5-haiku-20241022` | Override Claude model |

## Typical workflow

```bash
# 1. Make some changes in your project
# 2. Stage + generate .gitignore
gb add

# 3. Review before committing (optional)
gb review

# 4. Commit with AI-generated message
gb commit

# 5. After a tricky merge
gb resolve
```

## Project structure

```
git_booster/
├── git_booster/
│   ├── cli.py              # CLI entry point (click)
│   ├── core/
│   │   └── git.py          # All git subprocess calls
│   ├── ai/
│   │   ├── client.py       # Anthropic client
│   │   └── prompts.py      # All prompt templates
│   └── commands/
│       ├── add.py          # gb add
│       ├── status.py       # gb status
│       ├── commit.py       # gb commit
│       ├── resolve.py      # gb resolve
│       └── review.py       # gb review
├── pyproject.toml
└── .env.example
```
