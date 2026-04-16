---
description: Start a full plan-code-analyze cycle with agent teams
allowed-tools: Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskGet, TaskList, TaskUpdate
---

# Full development cycle: $ARGUMENTS

> **$ARGUMENTS**

## Step 1: Create the team and tasks

Call `TeamCreate` with team_name `"cycle"`.

Then create these four tasks with dependencies:

1. **TaskCreate**: "Plan: $ARGUMENTS"
   - Description: Research the topic, write plan to docs/plans/, create implementation subtasks
   - No blockers

2. **TaskCreate**: "Implement: $ARGUMENTS"
   - Description: Read plan, install deps, implement code in src/ and tests in tests/
   - `addBlockedBy`: [task 1]

3. **TaskCreate**: "Review: $ARGUMENTS"
   - Description: Review code against plan success criteria, write analysis, verdict
   - `addBlockedBy`: [task 2]

4. **TaskCreate**: "Commit: $ARGUMENTS"
   - Description: Run pre-commit checks, stage files, create conventional commit
   - `addBlockedBy`: [task 3]

## Step 2: Spawn all four teammates at once

Spawn all four in a single message using the Agent tool with `team_name: "cycle"`:

1. **planner** — `subagent_type: "planner"`, `team_name: "cycle"`, `name: "planner"`
2. **coder** — `subagent_type: "coder"`, `team_name: "cycle"`, `name: "coder"`
3. **analyst** — `subagent_type: "analyst"`, `team_name: "cycle"`, `name: "analyst"`
4. **git-ops** — `subagent_type: "git-ops"`, `team_name: "cycle"`, `name: "git-ops"`

Each teammate's spawn prompt should include the task description from
$ARGUMENTS so they have full context without needing the lead's history.

## Step 3: Monitor passively

Do NOT orchestrate. Do NOT read files the teammates are writing.
Do NOT re-run tests. The teammates self-organize:

- Each checks TaskList on startup
- Each claims their unblocked task
- Blocked teammates wait until dependencies complete
- Teammates message each other directly (analyst → coder for fixes)

**Only intervene if**:
- A teammate messages you asking for help
- A teammate has been idle for an extended period with uncompleted tasks
- You need to nudge a stuck teammate

## Step 4: Handle revision rounds

If the analyst sends a `needs_revision` verdict:
- The analyst will message the coder directly with fixes
- The analyst will create new fix tasks
- Let the coder and analyst coordinate — do not mediate
- Cap at 2 revision rounds. If still failing, report to user.

## Step 5: Shutdown and cleanup

After git-ops confirms the commit:
1. Send `{"type": "shutdown_request"}` to all four teammates
2. Wait for shutdown confirmations
3. Call `TeamDelete` to clean up team resources
4. Report to the user:
   - What was built (files created/modified)
   - Analyst verdict and key findings
   - Git commit hash
   - Any remaining issues or next steps
