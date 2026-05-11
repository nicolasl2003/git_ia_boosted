# git-booster

Local AI-powered Git — 100% private, 0% cloud, fully automated.

git-booster is a smart Git wrapper using Ollama (or Anthropic/OpenAI) to automate repetitive tasks entirely on your machine:

- Smart commit message generation (Conventional Commits)
- Automatic .gitignore creation and update
- Full merge/rebase conflict resolution
- Intelligent push-error recovery
- Code review before commit
- Smart branch management with AI-generated names
- Extensible skills system (YAML or Python)
- Zero external APIs required. Zero data leaks. No complex setup.

---

## Commands

### Native (no AI — instant)

| Command | Description |
|---|---|
| `gai status` | git status native output |
| `gai rm <file>` | Untrack file (keeps it on disk) |
| `gai rm <file> --hard` | Untrack + delete from disk (with confirmation) |
| `gai stop` | Stop Ollama server, free memory |
| `gai config` | Interactive setup: provider, model, keys |
| `gai skills` | List all available skills |
| `gai skills list` | Same — optionally filter with `-t <trigger>` |

### AI-powered (requires Ollama or API key)

| Command | Description |
|---|---|
| `gai add` | git add . + AI-generated/updated .gitignore |
| `gai add <file>` | Stage specific file + update .gitignore |
| `gai commit` | Generate commit message → validate → commit → push |
| `gai resolve` | Full conflict resolution + push-error recovery |
| `gai review` | AI code review of staged changes |
| `gai branch` | Smart branch management (create, list, switch, delete, clean) |
| `gai skill <name>` | Run a skill (e.g. `gai skill explain main.py`) |

---

## Requirements

- Python 3.10+
- Git
- Ollama (auto-installed on first run) or an Anthropic/OpenAI API key

---

## Installation

```bash
git clone <repo_url> ~/git_booster
cd ~/git_booster
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
gai config
```

On first `gai config`, choose your provider:

- **Ollama** (recommended) — local, free, private
- **Anthropic** — Claude via API key
- **OpenAI / OpenRouter** — GPT or any OpenAI-compatible endpoint

---

## Configuration

Settings stored in `~/.config/git-booster/config.env`.

| Variable | Default | Description |
|---|---|---|
| `GAI_PROVIDER` | `ollama` | `ollama` / `anthropic` / `openai` |
| `GAI_MODEL` | `llama3.2` | Model name |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `ANTHROPIC_API_KEY` | — | Required for Anthropic provider |
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override for OpenRouter etc. |

Environment variables always take priority over the config file.

---

## gai commit

```
A.I is processing...

┌─ Generated commit message ──────────────────────────┐
│ feat(config): add interactive provider setup command │
└─────────────────────────────────────────────────────┘

What do you want to do? [commit/edit/regenerate/abort] (commit):
```

| Choice | Action |
|---|---|
| `commit` | Commit as-is |
| `edit` | Open in `$EDITOR` (nano by default) |
| `regenerate` | Describe how to rewrite → AI regenerates |
| `abort` | Cancel |

After commit, if a remote is configured:

```
Push to remote? [y/N]
→ git push origin main
✓ Push succeeded.
```

---

## gai resolve

Handles the complete cycle: conflicts → resolution → push, in a single execution.

### What it does

- Detects the current state of the repo (rebase in progress, merge conflicts, clean tree)
- Stashes uncommitted changes automatically before any pull, restores them after
- Resolves all conflicts in one AI pass
- Continues the rebase automatically after resolution (up to 3 steps)
- Pushes after a clean resolution

### Push error recovery

| Error | Automatic fix |
|---|---|
| Remote ahead | `git pull` (auto rebase/merge) → re-push |
| No upstream branch | `git push --set-upstream origin <branch>` |
| Bad refspec | List remote branches, pick target or create new |
| Authentication failure | Instructions: SSH key, PAT, credentials |
| Remote not found | Instructions: check URL, network, VPN |
| Unknown error | Show raw error + AI explanation |

### Strategy selection

| Condition | Strategy |
|---|---|
| Linear history (no merge commits) | rebase |
| Single local commit | rebase |
| Merge commits in history | merge |

### Example

```
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

## gai branch

Smart branch management with AI-generated names.

### Subcommands

| Command | Description |
|---|---|
| `gai branch create` | AI generates a branch name from your description |
| `gai branch list` | List all local and remote branches |
| `gai branch switch` | Interactively switch to an existing branch |
| `gai branch delete` | Delete a branch (with confirmation) |
| `gai branch clean` | Delete all merged branches automatically |

### Example

```
$ gai branch create
Describe your feature: add user authentication with JWT

A.I is processing...

┌─ Suggested branch name ─────────────────┐
│ feat/user-authentication-jwt            │
└─────────────────────────────────────────┘

Create this branch? [Y/n]: y
✓ Switched to new branch feat/user-authentication-jwt
```

---

## Skills system

Skills extend gai with custom commands. Two formats supported: YAML (simple) and Python (advanced).

### YAML skill

```yaml
name:        deploy
description: "Deploy to production"
trigger:     manual
action: |
  echo "Deploying..."
  make deploy
  echo "Done."
```

### Python skill

```python
NAME        = "lint"
DESCRIPTION = "Run linter before commit"
TRIGGER     = "pre-commit"

def run(args: list[str], path: str | None = None) -> None:
    import subprocess
    subprocess.run(["flake8", "."], cwd=path)
```

### Skill fields

| Field | Required | Values |
|---|---|---|
| `name` | yes | Command name used in `gai skill <name>` |
| `description` | no | Shown in `gai skills list` |
| `trigger` | no | `manual` (default), `pre-commit`, `post-commit`, `post-push` |
| `action` | yes (YAML) | Shell command or multi-line script |

### Commands

```bash
gai skills
gai skills list
gai skills list -t pre-commit
gai skill deploy
gai skill explain main.py
```

### Auto-discovery

| Location | Who adds it |
|---|---|
| `git_booster/skills/` | Built-in |
| `~/.config/git-booster/skills/` | Your custom skills |

### Built-in skills

| Name | Trigger | Description |
|---|---|---|
| `explain` | manual | AI explanation of a file or staged diff |
| `hello` | manual | Example skill / template |
| `check` | pre-commit | Show git status + last 3 commits |
| `deploy` | manual | Deployment hook template |

---

## Typical workflow

```bash
gai status
gai add
gai review
gai commit
gai resolve
gai skill deploy
gai stop
```

---

## Project structure

```
git_booster/
├── git_booster/
│   ├── cli.py
│   ├── core/
│   │   └── git.py
│   ├── ai/
│   │   ├── client.py
│   │   └── prompts.py
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── explain.py
│   │   ├── hello.py
│   │   ├── check.yaml
│   │   └── deploy.yaml
│   └── commands/
│       ├── add.py
│       ├── branch.py
│       ├── commit.py
│       ├── config.py
│       ├── resolve.py
│       ├── review.py
│       ├── rm.py
│       ├── status.py
│       └── stop.py
├── .env.example
└── pyproject.toml
```

---

## License

MIT License

Copyright (c) 2024 git-booster contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Open-source dependencies

| Dependency | License | Role |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) | MIT | Local AI model server |
| [Click](https://github.com/pallets/click) | BSD-3-Clause | CLI framework |
| [Rich](https://github.com/Textualize/rich) | MIT | Terminal formatting |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Config file loading |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | MIT | Anthropic API client |
| [openai](https://github.com/openai/openai-python) | Apache-2.0 | OpenAI API client |
| [GitPython](https://github.com/gitpython-developers/GitPython) | BSD-3-Clause | Git repository interaction |

---

## Contributing

Contributions are welcome. By contributing to git-booster, you agree that your contributions will be licensed under the MIT License.

1. Fork the repository
2. Create a feature branch: `gai branch create`
3. Commit your changes: `gai commit`
4. Push and open a Pull Request