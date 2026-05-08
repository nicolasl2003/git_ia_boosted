# git-booster

**Local AI-powered Git — 100% private, 0% cloud, fully automated.**

`git-booster` is a smart Git wrapper using **Ollama** (or Anthropic/OpenAI) to automate repetitive tasks entirely on your machine:

- Smart commit message generation (Conventional Commits)
- Automatic `.gitignore` creation and update
- Full merge/rebase conflict resolution
- Intelligent push-error recovery
- Code review before commit
- Extensible skills system (YAML or Python)

**Zero external APIs required. Zero data leaks. No complex setup.**

---

## Commands

### Native (no AI — instant)

| Command                  | Description                                        |
|--------------------------|----------------------------------------------------|
| `gai status`             | `git status` native output                         |
| `gai rm <file>`          | Untrack file (keeps it on disk)                    |
| `gai rm <file> --hard`   | Untrack + delete from disk (with confirmation)     |
| `gai stop`               | Stop Ollama server, free memory                    |
| `gai config`             | Interactive setup: provider, model, keys           |
| `gai skills`             | List all available skills                          |
| `gai skills list`        | Same — optionally filter with `-t <trigger>`       |

### AI-powered (requires Ollama or API key)

| Command                  | Description                                        |
|--------------------------|----------------------------------------------------|
| `gai add`                | `git add .` + AI-generated/updated `.gitignore`    |
| `gai add <file>`         | Stage specific file + update `.gitignore`          |
| `gai commit`             | Generate commit message → validate → commit → push |
| `gai resolve`            | Full conflict resolution + push-error recovery     |
| `gai review`             | AI code review of staged changes                   |
| `gai skill <name>`       | Run a skill (e.g. `gai skill explain main.py`)     |

---

## Requirements

- Python 3.10+
- Git
- Ollama (auto-installed on first run) **or** an Anthropic/OpenAI API key

---

## Installation

```bash
# 1. Clone
git clone <repo_url> ~/git_booster

# 2. Create virtualenv and install
cd ~/git_booster
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Configure (provider, model, keys)
gai config
```

On first `gai config`, choose your provider:
- **Ollama** (recommended) — local, free, private
- **Anthropic** — Claude via API key
- **OpenAI / OpenRouter** — GPT or any OpenAI-compatible endpoint

---

## Configuration

Settings stored in `~/.config/git-booster/config.env`.

| Variable            | Default                    | Description                      |
|---------------------|----------------------------|----------------------------------|
| `GAI_PROVIDER`      | `ollama`                   | `ollama` / `anthropic` / `openai`|
| `GAI_MODEL`         | `llama3.2`                 | Model name                       |
| `OLLAMA_HOST`       | `http://localhost:11434`   | Ollama server URL                |
| `ANTHROPIC_API_KEY` | —                          | Required for Anthropic provider  |
| `OPENAI_API_KEY`    | —                          | Required for OpenAI provider     |
| `OPENAI_BASE_URL`   | `https://api.openai.com/v1`| Override for OpenRouter etc.     |

Environment variables always take priority over the config file.

---

## `gai commit` — workflow

```
A.I is processing...

┌─ Generated commit message ──────────────────────────┐
│ feat(config): add interactive provider setup command │
└─────────────────────────────────────────────────────┘

What do you want to do? [commit/edit/regenerate/abort] (commit):
```

| Choice       | Action                                           |
|--------------|--------------------------------------------------|
| `commit`     | Commit as-is                                     |
| `edit`       | Open in `$EDITOR` (nano by default)              |
| `regenerate` | Describe how to rewrite → AI regenerates         |
| `abort`      | Cancel                                           |

After commit, if a remote is configured:
```
Push to remote? [y/N]
→ git push origin main
✓ Push succeeded.
```
Push errors are handled automatically (see `gai resolve`).

---

## `gai resolve` — full conflict resolution

`gai resolve` handles the complete cycle: conflicts → resolution → push, in a **single execution**.

### What it does

```
gai resolve
```

1. **Detects the current state** of the repo:
   - Rebase in progress with conflicts
   - Merge conflicts in working tree
   - Clean tree → attempts push directly

2. **Stashes uncommitted changes** automatically before any pull, restores them after.

3. **Resolves all conflicts in one AI pass** — no repeated prompts per block.

4. **Continues the rebase** automatically after resolution (up to 3 steps).

5. **Pushes** after a clean resolution.

### Push error recovery

When a push fails, `gai resolve` detects the cause and fixes it automatically:

| Error                      | Automatic fix                                       |
|----------------------------|-----------------------------------------------------|
| Remote ahead (fetch first) | `git pull` (auto rebase/merge) → re-push            |
| No upstream branch         | `git push --set-upstream origin <branch>`           |
| Bad refspec                | List remote branches, pick target or create new     |
| Authentication failure     | Instructions: SSH key, PAT, credentials             |
| Remote not found           | Instructions: check URL, network, VPN               |
| Unknown error              | Show raw error + AI explanation                     |

### Strategy selection

The rebase/merge strategy is chosen automatically:

| Condition                        | Strategy |
|----------------------------------|----------|
| Linear history (no merge commits)| rebase   |
| Single local commit              | rebase   |
| Merge commits in history         | merge    |

The recommended strategy is shown before execution. You can override it.

### Anti-loop guard

If conflicts keep appearing after repeated pulls (e.g. circular dependencies), `gai resolve` stops after **3 attempts** and shows clear instructions for manual resolution.

### Example workflow

```bash
# Scenario: you have uncommitted changes + remote is ahead

$ gai resolve

── Push — main → origin ────────────────────────────────
→ git push origin main

Push failed  (remote ahead)
Remote has commits you don't have.
Pull now? [Y/n]:

Uncommitted changes stashed → stash@{0}

Recommended: rebase  (linear history)
  1. rebase  (recommended)
  2. merge
  q. abort
Strategy [1/2/q] (1): 1

→ git pull --rebase origin main
Pull succeeded.
Stash restored.

→ Retrying push…
✓ Push succeeded.
```

---

## Skills system

Skills extend `gai` with custom commands. Two formats are supported: **YAML** (simple) and **Python** (advanced).

### YAML skill

Create a `.yaml` file in `~/.config/git-booster/skills/`:

```yaml
# ~/.config/git-booster/skills/deploy.yaml

name:        deploy
description: "Deploy to production"
trigger:     manual          # manual | pre-commit | post-commit | post-push
action: |
  echo "Deploying..."
  make deploy
  echo "Done."
```

### Python skill

Create a `.py` file in `~/.config/git-booster/skills/`:

```python
# ~/.config/git-booster/skills/lint.py

NAME        = "lint"
DESCRIPTION = "Run linter before commit"
TRIGGER     = "pre-commit"

def run(args: list[str], path: str | None = None) -> None:
    import subprocess
    subprocess.run(["flake8", "."], cwd=path)
```

### Skill fields

| Field         | Required | Values                                          |
|---------------|----------|-------------------------------------------------|
| `name`        | yes      | Command name used in `gai skill <name>`         |
| `description` | no       | Shown in `gai skills list`                      |
| `trigger`     | no       | `manual` (default), `pre-commit`, `post-commit`, `post-push` |
| `action`      | yes (YAML)| Shell command or multi-line script             |

### Commands

```bash
gai skills                      # list all skills
gai skills list                 # same
gai skills list -t pre-commit   # filter by trigger

gai skill deploy                # run a skill manually
gai skill explain main.py       # run explain skill on a file
```

### Auto-discovery

Skills are loaded from two locations (no registration needed):

| Location                              | Who adds it   |
|---------------------------------------|---------------|
| `git_booster/skills/`                 | Built-in      |
| `~/.config/git-booster/skills/`       | Your custom skills |

### Built-in skills

| Name      | Trigger    | Description                              |
|-----------|------------|------------------------------------------|
| `explain` | manual     | AI explanation of a file or staged diff  |
| `hello`   | manual     | Example skill / template                 |
| `check`   | pre-commit | Show `git status` + last 3 commits       |
| `deploy`  | manual     | Deployment hook template                 |

---

## Typical workflow

```bash
# 1. Check state (instant)
gai status

# 2. Stage everything + generate .gitignore
gai add

# 3. Optional: review before committing
gai review

# 4. Commit with AI message + push
gai commit

# 5. Handle conflicts or push errors
gai resolve

# 6. Run a custom skill
gai skill deploy

# 7. Free resources
gai stop
```

---

## Project structure

```
git_booster/
├── git_booster/
│   ├── cli.py                   # CLI entry point (click)
│   ├── core/
│   │   └── git.py               # All git subprocess calls
│   ├── ai/
│   │   ├── client.py            # Multi-provider client (Ollama/Anthropic/OpenAI)
│   │   └── prompts.py           # Prompt templates
│   ├── skills/
│   │   ├── __init__.py          # Auto-discovery engine (Python + YAML)
│   │   ├── explain.py           # Built-in: explain file or diff
│   │   ├── hello.py             # Built-in: template / smoke-test
│   │   ├── check.yaml           # Built-in: pre-commit status check
│   │   └── deploy.yaml          # Built-in: deploy hook template
│   └── commands/
│       ├── add.py               # gai add
│       ├── commit.py            # gai commit
│       ├── config.py            # gai config
│       ├── resolve.py           # gai resolve
│       ├── review.py            # gai review
│       ├── rm.py                # gai rm
│       ├── status.py            # gai status
│       └── stop.py              # gai stop
├── .env.example
└── pyproject.toml
```
