# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Multi-agent GPU driver development framework using Python, powered by Claude Code Agent Teams. All agents read this file automatically on startup.

## Toolchain

- **Package manager**: `uv` — NEVER use pip directly
- **Formatter/linter**: `ruff` — auto-runs via PostToolUse hook on every Edit/Write
- **Testing**: `pytest` via `uv run pytest`
- **Python**: 3.12+ (managed by uv via `.python-version`)

## Commands

```bash
uv sync                                  # install all dependencies
uv run pytest                            # run all tests
uv run pytest tests/test_foo.py -v       # run a single test file
uv run pytest tests/test_foo.py::test_x  # run a single test function
uv run pytest --cov=src                  # run tests with coverage
uv run ruff check .                      # lint
uv run ruff format .                     # format (also auto via hook)
uv add <package>                         # add a dependency
uv add --group dev <pkg>                 # add a dev dependency
```

## Critical rules

- Install packages with `uv add <package>` (NOT pip install)
- Run scripts with `uv run <script.py>` (NOT python <script.py>)
- After cloning, run `uv sync` to set up the environment

## Code conventions

- Ruff line-length is **100** characters
- Ruff enforces: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-simplify, ruff-specific rules
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- One module per file, keep files under 300 lines
- Tests mirror src/ structure: `src/foo/bar.py` → `tests/test_bar.py`
- pytest `pythonpath` is set to `["src"]`, so imports use `from module import ...` not `from src.module import ...` in tests

## Agent team architecture

This project uses Claude Code Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).

### Slash commands

- `/cycle <task>` — full plan → code → analyze → commit cycle
- `/research <topic>` — parallel research from multiple angles

### Agent roles and boundaries

| Agent | Reads | Writes | Model | maxTurns |
|-------|-------|--------|-------|----------|
| Planner | feedback-log, codebase, web | docs/plans/ | opus | 30 |
| Coder | plans, tasks | src/, tests/ | opus | 50 |
| Analyst | plans, code diffs, test results | docs/analysis/, feedback-log.json | sonnet | 20 |
| Git Ops | everything | git operations | sonnet | 15 |
| LaTeX | analysis, plans | docs/reports/ | sonnet | 20 |
| Dashboard | tasks, analysis | web UI files | sonnet | 15 |

Each agent owns its directories — no cross-writing.

### Coordination flow

```
Planner ──plan──→ Coder ←──fixes──→ Analyst ──approve──→ Git Ops
   ↑                                    │
   └──────── feedback-log.json ─────────┘
```

The analyst can request up to 2 rounds of revisions from the coder
before the cycle completes. After analyst approval, git-ops commits.

### Task coordination

- Use the **built-in task system** (TaskCreate/TaskUpdate/TaskList) for
  cross-agent coordination — not hand-rolled JSON files
- Teammates message each other directly via SendMessage for handoffs
- `agents/shared-state/feedback-log.json` — analyst → planner feedback loop (persists across cycles)

## Directory layout

```
src/                     ← production code
tests/                   ← test files (conftest.py has shared fixtures)
docs/plans/              ← planner agent writes here
docs/analysis/           ← analyst agent writes here
docs/reports/            ← LaTeX reports
agents/shared-state/     ← task-list.json, feedback-log.json
.claude/agents/          ← subagent role definitions
.claude/commands/        ← slash command definitions (cycle, research)
.claude/hooks/           ← auto-format (ruff) + uv reminder hooks
```
