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

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2024 git-booster contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Open-source dependencies

git-booster is built on top of open-source tools and libraries:

| Dependency | License | Role |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) | MIT | Local AI model server |
| [Python](https://www.python.org) | PSF License | Runtime |
| [Click](https://github.com/pallets/click) | BSD-3-Clause | CLI framework |
| [Rich](https://github.com/Textualize/rich) | MIT | Terminal formatting |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD-3-Clause | Config file loading |
| [anthropic](https://github.com/anthropics/anthropic-sdk-python) | MIT | Anthropic API client |
| [openai](https://github.com/openai/openai-python) | Apache-2.0 | OpenAI API client |
| [GitPython](https://github.com/gitpython-developers/GitPython) | BSD-3-Clause | Git repository interaction |

> All dependencies are optional except Click and Rich.
> Ollama, anthropic and openai are only required depending on your chosen provider.

### Contributing

Contributions are welcome! By contributing to git-booster, you agree that your contributions will be licensed under the MIT License.

1. Fork the repository
2. Create a feature branch: `gai branch create`
3. Commit your changes: `gai commit`
4. Push and open a Pull Request

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

## gai commit — workflow

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

Push errors are handled automatically (see `gai resolve`).

---

## gai resolve — full conflict resolution

`gai resolve` handles the complete cycle: conflicts → resolution → push, in a single execution.

### What it does

```
gai resolve
```

Detects the current state of the repo:

- Rebase in progress with conflicts
- Merge conflicts in working tree
- Clean tree → attempts push directly

- Stashes uncommitted changes automatically before any pull, restores them after.
- Resolves all conflicts in one AI pass — no repeated prompts per block.
- Continues the rebase automatically after resolution (up to 3 steps).
- Pushes after a clean resolution.

### Push error recovery

| Error | Automatic fix |
|---|---|
| Remote ahead (fetch first) | `git pull` (auto rebase/merge) → re-push |
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

The recommended strategy is shown before execution. You can override it.

### Anti-loop guard

If conflicts keep appearing after repeated pulls, `gai resolve` stops after 3 attempts and shows clear instructions for manual resolution.

### Example workflow

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

## gai branch — smart branch management

`gai branch` handles the full branch lifecycle with AI-generated names and automatic stash management.

### Commands

| Command | Aliases | Description |
|---|---|---|
| `gai branch` | | Interactive menu |
| `gai branch create` | `new` | AI-generated branch name from your description |
| `gai branch list` | `ls` | List all branches with date & author |
| `gai branch switch` | `checkout`, `sw` | Interactive branch switcher |
| `gai branch rm [name]` | `delete`, `remove` | Delete a branch locally and optionally on remote |
| `gai branch clean` | `prune` | Delete all merged branches |
| `gai branch --help` | `-h`, `help` | Show all commands and options |

### Branch types

```
feat  fix  hotfix  refactor  chore  docs  test  release
```

### gai branch create — workflow

```
$ gai branch create

Type [feat/fix/hotfix/...]: feat
Ticket / issue number: 42
Describe your feature/fix: add user authentication

A.I is generating branch name...

Suggested branch name: feat/42-add-user-authentication

Use this name? [yes/edit/abort] (yes):
Stash changes before creating branch? [Y/n]:
✓ Changes stashed.
✓ Branch 'feat/42-add-user-authentication' created and checked out.
Push to remote? [Y/n]:
✓ Pushed to origin/feat/42-add-user-authentication.
✓ Stash restored.
```

### gai branch rm — workflow

```
$ gai branch rm fix/old-feature

Branch to delete: fix/old-feature
Delete this branch locally? [y/N]: y
✓ Local branch 'fix/old-feature' deleted.
Also delete 'origin/fix/old-feature' on remote? [y/N]: y
✓ Remote branch 'origin/fix/old-feature' deleted.
```

- Safe delete by default (`-d`) — warns if branch is not fully merged
- Force delete option (`-D`) with explicit confirmation
- Cannot delete the currently checked-out branch
- Automatically detects if branch exists on remote

### gai branch list — example output

```
  ●  main                  2024-01-15  Alice
     feat/42-auth          2024-01-14  Bob      remote
     fix/login-crash       2024-01-13  Alice
```

### Auto stash

Any `gai branch` command that switches context (create, switch) automatically:

1. Detects uncommitted changes
2. Asks to stash before switching
3. Restores stash after the operation

---

## Skills system

Skills extend `gai` with custom commands. Two formats: YAML (simple) and Python (advanced).

### YAML skill

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

| Field | Required | Values |
|---|---|---|
| `name` | yes | Command name used in `gai skill <name>` |
| `description` | no | Shown in `gai skills list` |
| `trigger` | no | `manual` (default), `pre-commit`, `post-commit`, `post-push` |
| `action` | yes (YAML) | Shell command or multi-line script |

### Commands

```bash
gai skills                      # list all skills
gai skills list                 # same
gai skills list -t pre-commit   # filter by trigger

gai skill deploy                # run a skill manually
gai skill explain main.py       # run explain skill on a file
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

# 6. Manage branches
gai branch create       # new feature branch
gai branch switch       # change branch
gai branch rm           # delete a branch
gai branch clean        # remove merged branches

# 7. Run a custom skill
gai skill deploy

# 8. Free resources
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
│       ├── branch.py            # gai branch
│       ├── commit.py            # gai commit
│       ├── config.py            # gai config
│       ├── resolve.py           # gai resolve
│       ├── review.py            # gai review
│       ├── rm.py                # gai rm
│       ├── status.py            # gai status
│       └── stop.py              # gai stop
├── LICENSE
├── .env.example
└── pyproject.toml
```
