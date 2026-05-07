"""
All prompt templates used by git-booster.
Each function returns a (system_prompt, user_prompt) tuple.
"""

# ---------------------------------------------------------------------------
# Commit message
# ---------------------------------------------------------------------------

COMMIT_SYSTEM = """\
You are an expert software engineer writing git commit messages.
Strict rules — violation is not acceptable:
- Format: type(scope): summary
- type: feat | fix | docs | refactor | test | chore | style | perf
- scope: the file or module most affected (short, lowercase, no path)
- summary: imperative, lowercase, ≤ 72 chars, no period at end
- ONE LINE ONLY. No body. No bullet points. No explanation.
- ABSOLUTELY NO markdown, no backticks, no fences, no asterisks.
- Output the commit message line and nothing else.
Examples of correct output:
  fix(cli): remove deprecated --flag option
  feat(commit): add push prompt after commit
  refactor(git): extract _run helper to core module
  docs(readme): update installation instructions
"""

def commit_prompt(diff: str, status: str, style_hint: str = "") -> tuple[str, str]:
    style = f"\nUser instruction: {style_hint}" if style_hint else ""
    user = f"""Staged diff:
{diff[:3000]}

Git status:
{status}
{style}
Write the commit message (one line only, no markdown)."""
    return COMMIT_SYSTEM, user


# ---------------------------------------------------------------------------
# .gitignore generation
# ---------------------------------------------------------------------------

GITIGNORE_SYSTEM = """\
You are an expert DevOps engineer generating .gitignore files.
Given a list of files in a project, detect the technologies, languages and frameworks used,
then produce an appropriate .gitignore.
Rules:
- Output ONLY the .gitignore content, no explanation, no markdown fences.
- Group rules by category with a comment header (e.g. # Python, # Node, # OS).
- Include common OS artefacts (macOS, Windows, Linux).
- Do not ignore source files.
"""

def gitignore_prompt(file_list: list[str], existing_gitignore: str = "") -> tuple[str, str]:
    files_str = "\n".join(file_list[:500])   # cap to avoid token explosion
    existing = f"\nExisting .gitignore:\n```\n{existing_gitignore}\n```" if existing_gitignore else ""
    user = f"""Project files:
```
{files_str}
```
{existing}
Generate the .gitignore file."""
    return GITIGNORE_SYSTEM, user


# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------

STATUS_SYSTEM = """\
You are a helpful git assistant. Given the output of `git status` and recent log,
write a concise human-friendly summary (3-6 lines max) that explains:
- What branch the developer is on
- What kind of changes are pending (new files, modifications, deletions)
- Any potential issues or reminders (e.g. uncommitted changes, untracked files)
Output plain text, no markdown, no bullet points.
"""

def status_prompt(status_output: str, log_output: str, branch: str) -> tuple[str, str]:
    user = f"""Branch: {branch}

git status:
{status_output}

Recent commits:
{log_output}

Summarise the current state of the repository."""
    return STATUS_SYSTEM, user


# ---------------------------------------------------------------------------
# Merge conflict resolution
# ---------------------------------------------------------------------------

CONFLICT_SYSTEM = """\
You are an expert software engineer resolving git merge conflicts.
You will receive the content of a file containing conflict markers (<<<<<<<, =======, >>>>>>>).
Your task:
- Analyse both sides of each conflict carefully.
- Produce a clean, correct merged file with ALL conflict markers removed.
- Preserve indentation, formatting and existing logic.
- Output ONLY the resolved file content, no explanation, no markdown fences.
"""

def conflict_prompt(filepath: str, content: str) -> tuple[str, str]:
    user = f"""File: {filepath}

```
{content}
```

Resolve all merge conflicts and return the complete file."""
    return CONFLICT_SYSTEM, user


# ---------------------------------------------------------------------------
# Code review
# ---------------------------------------------------------------------------

REVIEW_SYSTEM = """\
You are a senior software engineer conducting a pre-commit code review.
Given a git diff, provide:
1. A brief overall assessment (1-2 sentences)
2. Issues found (bugs, security, performance, style) — list only real problems
3. Suggestions for improvement (optional)

Be concise, direct, and actionable. Use plain text with minimal formatting.
If there are no issues, say so clearly.
"""

def review_prompt(diff: str, status: str) -> tuple[str, str]:
    user = f"""Staged diff to review:

```diff
{diff}
```

Git status:
```
{status}
```

Review these changes."""
    return REVIEW_SYSTEM, user
