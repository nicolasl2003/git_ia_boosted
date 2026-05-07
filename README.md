# git-booster

AI-powered Git wrapper using **local Ollama** — no API key, no cloud, runs entirely on your machine.

Automates commit messages, `.gitignore` generation, merge conflict resolution, and code review.

---

## Commands

### Native (no AI — instant, no Ollama needed)

| Command              | Description                                          |
|----------------------|------------------------------------------------------|
| `gai status`         | `git status` native output                           |
| `gai rm <file>`      | Untrack file (keeps on disk)                         |
| `gai rm <file> --hard` | Untrack + delete file from disk (with confirmation)|
| `gai stop`           | Stop Ollama server, free memory/CPU                  |
| `gai config`         | Interactive setup: provider, model, Ollama           |
| `gai skills`         | List available AI skills                             |

### AI-powered (requires Ollama running)

| Command              | Description                                          |
|----------------------|------------------------------------------------------|
| `gai add`            | `git add .` + AI-generated/updated `.gitignore`      |
| `gai commit`         | Generate commit message → validate → commit → push   |
| `gai resolve`        | Detect and resolve merge conflicts                   |
| `gai review`         | Code review of staged changes                        |
| `gai skill <name>`   | Run a specific AI skill (e.g. `gai skill explain`)   |

---

## Requirements

- Python 3.10+
- Git
- `curl` (for Ollama auto-install)

> Ollama is installed and started **automatically** on first run. No manual setup needed.

---

## Installation

### 1. Clone and add to your shell

```bash
git clone <repo_url> ~/git_booster
echo 'alias gai="$HOME/git_booster/gai"' >> ~/.zshrc
source ~/.zshrc
```

### 2. First run — fully automatic

```bash
gai config
```

On first run, `gai` automatically:
1. Creates the Python `.venv` and installs dependencies
2. Installs Ollama if not present (via official install script)
3. Starts the Ollama server in the background
4. Pulls the configured model (default: `qwen2.5-coder:3b`)

Everything is handled without any manual commands. You only need to run `gai config` once to choose your model.

### 3. That's it

```bash
# From any git repo:
gai commit
```

---

## Configuration

Settings are stored in `~/.config/git-booster/config.env` (created by `gai config`).

| Variable            | Default                  | Description                      |
|---------------------|--------------------------|----------------------------------|
| `GAI_PROVIDER`      | `ollama`                 | AI provider                      |
| `OLLAMA_HOST`       | `http://localhost:11434` | Ollama server URL                |
| `GAI_MODEL`         | `llama3.2`               | Model to use                     |
| `ANTHROPIC_API_KEY` | —                        | Only if using Anthropic provider |
| `OPENAI_API_KEY`    | —                        | Only if using OpenAI provider    |

The `gai` wrapper script automatically loads this file. No need to export variables manually.

---

## `gai config` — interactive setup

```
git-booster — configuration
────────────────────────────
Current configuration
  Provider    ollama
  Model       qwen2.5-coder:3b
  Ollama host http://localhost:11434

Select AI provider:
  1. ollama       Local Ollama (no API key, recommended)
  2. anthropic    Anthropic Claude (API key required)
  3. openai       OpenAI (API key required)

Provider [1/2/3] (1):

Select a model:
  1. qwen2.5-coder:3b    Best for code — GTX 1050 Ti (4GB) ~2GB VRAM
  2. qwen2.5-coder:1.5b  Lightest — GTX 1050 2GB / CPU only
  3. llama3.2:3b         General purpose — 4GB VRAM
  4. mistral:7b          Powerful — needs 8GB+ VRAM
  5. Enter custom model name

Configuration saved to ~/.config/git-booster/config.env
```

---

## `gai commit` — workflow

```
[ git-booster ] provider: ollama | model: qwen2.5-coder:3b | host: http://localhost:11434

A.I is processing...

┌─ Generated commit message ──────────────────────────┐
│ feat(config): add interactive provider setup command │
└─────────────────────────────────────────────────────┘

What do you want to do? [commit/edit/regenerate/abort] (commit):
```

| Choice       | Action                                                    |
|--------------|-----------------------------------------------------------|
| `commit`     | Commit as-is                                              |
| `edit`       | Open message in `$EDITOR` (nano by default)               |
| `regenerate` | Describe how you want the commit, AI rewrites it          |
| `abort`      | Cancel                                                    |

After commit, if remotes are configured:
```
Push to remote? [y/N]
```
If multiple remotes exist, you can choose one or push to all.

---

## Typical workflow

```bash
# 1. Check what changed (instant, no AI)
gai status

# 2. Stage and generate .gitignore
gai add

# 3. (Optional) Review before committing
gai review

# 4. Commit with AI message + push
gai commit

# 5. After a tricky merge
gai resolve

# 6. Free resources when done
gai stop
```

---

## Skills system

Skills are modular AI capabilities. Drop a `.py` file in `git_booster/skills/` and it's auto-discovered.

```bash
gai skills                    # list available skills
gai skill explain             # explain current staged diff
gai skill explain main.py     # explain a specific file
```

**Adding a custom skill** — create `git_booster/skills/myskill.py`:

```python
NAME        = "myskill"
DESCRIPTION = "Does something useful"

def run(args: list[str], path: str | None = None) -> None:
    ...
```

---

## Project structure

```
git_booster/
├── gai                          # Shell wrapper — auto .venv, Ollama, model pull
├── git_booster/
│   ├── cli.py                   # CLI entry point (click)
│   ├── core/
│   │   └── git.py               # All git subprocess calls
│   ├── ai/
│   │   ├── client.py            # Ollama HTTP client (no external deps)
│   │   └── prompts.py           # Prompt templates
│   ├── skills/
│   │   ├── __init__.py          # Auto-discovery engine
│   │   └── explain.py           # Built-in skill: explain file/diff
│   └── commands/
│       ├── config.py            # gai config
│       ├── add.py               # gai add
│       ├── status.py            # gai status (native)
│       ├── commit.py            # gai commit
│       ├── rm.py                # gai rm
│       ├── stop.py              # gai stop
│       ├── resolve.py           # gai resolve
│       └── review.py            # gai review
├── .env.example
└── pyproject.toml
```
