---
description: Start a full plan-code-analyze cycle with agent teams
allowed-tools: Agent, SendMessage, TaskCreate, TaskGet, TaskList, TaskUpdate
---

# Full development cycle: $ARGUMENTS

Run a plan → code → analyze → commit cycle using agent teams.

> **$ARGUMENTS**

## Phase 1: Planning

Spawn a **planner** teammate to:
- Research the topic (web search if needed)
- Read `agents/shared-state/feedback-log.json` for past lessons
- Write plan to `docs/plans/`
- List any `uv add` commands needed
- Create tasks via TaskCreate (NOT via task-list.json)
- Message you when the plan is ready

Wait for the planner to signal "plan complete" before proceeding.

## Phase 2: Implementation

Spawn a **coder** teammate to:
- Read the plan from `docs/plans/`
- Run `uv add` commands from the plan
- Pick up tasks and implement them (update task status as they go)
- Run `uv run pytest` after each change
- Run the completion checklist before signaling done
- Message you when all tasks are complete

Wait for the coder to signal "implementation complete" before proceeding.

## Phase 3: Analysis

Spawn an **analyst** teammate to:
- Review code against the plan's success criteria
- Run `uv run pytest --cov=src` and `uv run ruff check .`
- Write findings to `docs/analysis/`
- Update `agents/shared-state/feedback-log.json`

The analyst will make a verdict: **approved** or **needs_revision**.

### If needs_revision (max 2 rounds):

The analyst will message the coder directly with specific fixes and
create new tasks. Let the coder fix the issues, then have the analyst
re-review. Cap at 2 revision rounds — if still failing after 2 rounds,
report the remaining issues to the user and stop.

### If approved:

Proceed to Phase 4.

## Phase 4: Git commit

After analyst approval, spawn a **git-ops** teammate to:
- Run `uv run pytest` and `uv run ruff check .` one final time
- Stage the changed files (src/, tests/, docs/)
- Create a conventional commit: `feat(<topic>): <description>`
- Do NOT push unless the user explicitly asked for it

Wait for git-ops to confirm the commit is done.

## Your role as team lead

- Orchestrate the phases sequentially: plan → code → analyze → commit
- Monitor each teammate's progress via TaskList
- If a teammate hits maxTurns without completing, inspect the state
  and either finish the remaining work yourself or re-dispatch
- After all phases complete, report to the user:
  - What was built (files created/modified)
  - Analyst verdict and key findings
  - Git commit hash
  - Any remaining issues or next steps

## Coordination rules

- Each teammate owns its directories — no cross-writing
- Use the built-in task system (TaskCreate/TaskUpdate) for coordination
- Teammates message each other via SendMessage for handoffs
- The team lead monitors and intervenes if stuck
