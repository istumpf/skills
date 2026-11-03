# OpenSpec Orchestrate

Apply an OpenSpec change through sequential delegation and review. You choose
the worker model; the parent agent stays in charge of scope, review, task
completion, and optional PR publication.

For each pending task group, the orchestrator starts a fresh worker, reviews its
implementation, and requests fixes from that same worker until the group is
accepted. Only then does it mark the tasks complete and start a new worker for
the next group.

## Requirements

- An OpenSpec project with a change ready for implementation and the OpenSpec CLI
  available in the implementation workspace.
- Codex or Claude Code with native workers that can implement code, select your
  requested model, and continue a worker for review fixes.
- The project's normal development tools and required validation commands.
- For stacked PR mode: Git, a configured remote, and authenticated access to the
  repository's PR service through an available integration or CLI.

Use a model available in the active host. This skill does not provide a bridge
between Codex and Anthropic models or between Claude Code and OpenAI models.
Some hosts accept model aliases directly; selecting an exact model ID may
require a configured custom agent. See [runtime notes](references/runtimes.md).

## Installation

Clone `istumpf/skills` if you do not already have a checkout:

```sh
git clone https://github.com/istumpf/skills.git
cd skills
```

From the **repository root**, link this skill into both global skill directories:

```sh
skill_dir="$PWD/skills/openspec-orchestrate"
for skill_home in "$HOME/.codex/skills" "$HOME/.claude/skills"; do
  mkdir -p "$skill_home"
  target="$skill_home/openspec-orchestrate"
  if [ -e "$target" ] || [ -L "$target" ]; then
    printf 'Already installed; leaving in place: %s\n' "$target"
  else
    ln -s "$skill_dir" "$target"
  fi
done
```

Both agents then read the same checkout. Keep that checkout at a stable path;
moving it requires updating these links. The commands skip existing installations,
including broken links. Compare any existing copy before choosing to replace it.

Alternatively, copy this entire directory into `~/.codex/skills/openspec-orchestrate`
or `~/.claude/skills/openspec-orchestrate`. Include `SKILL.md` and `references/`;
the repository's `tests/` directory is not required to use the skill.
Start a new agent session if the skill does not appear in the current session.

## Basic usage

Start the orchestrator in the project where the implementation belongs.

In Codex:

```text
$openspec-orchestrate <change-name> using worker model <model>
```

In Claude Code:

```text
/openspec-orchestrate <change-name> using worker model <model>
```

Replace the placeholders with your change and a model supported by your host.
You can also specify a supported reasoning effort in natural language. The
parent keeps its current model; only the workers use your selected model.

If you omit the change, the orchestrator uses an unambiguous change from context
or the sole active change; otherwise it asks you to choose. If no worker model
has been specified for the run, it asks before spawning. It reports an unavailable
model or missing runtime capability instead of silently substituting a model.

For a registered OpenSpec store, name the store in the request. The orchestrator
keeps the planning store separate from the implementation workspace and carries
the store selection through subsequent OpenSpec commands.

## How groups and review work

A group normally corresponds to one section in the task artifact, such as
`## 2. API`, including its tasks and subordinate headings. Groups run in their
written order. Already completed groups are skipped; only unchecked tasks are
assigned within a partially completed group.

1. The orchestrator reads the change context and repository instructions, records
   existing edits, and captures a baseline for the next group.
2. A new worker implements exactly that group's pending tasks and reports its
   changes and validation results. It leaves task markers and Git operations
   to the orchestrator.
3. The orchestrator inspects the actual code and relevant spec scenarios and
   checks the validation evidence. Actionable findings go back to the same worker.
4. Review and fixes repeat until the group passes. There is no fixed review-round
   cap, but a genuine blocker or lack of progress is surfaced for resolution.
5. The orchestrator marks accepted tasks complete and moves to a fresh worker
   for the next group. After the last group, it checks the combined result and
   runs the remaining change-level validation.

The default mode leaves accepted changes in the workspace. Applying alone does
not request commits or PR publication. Neither mode automatically merges PRs or
archives the OpenSpec change.

## One stacked PR per group

Opt in by appending `with one stacked PR per group`:

```text
$openspec-orchestrate <change-name> using worker model <model> with one stacked PR per group
```

Use the same wording with `/openspec-orchestrate` in Claude Code. A generic request
to open a PR does not select this mode. You may also name a target base branch;
otherwise the orchestrator uses the repository or workspace setting.

| PR | Contains | Targets |
| --- | --- | --- |
| First | First processed group's changes and completion markers | Selected repository base |
| Second | Next group's changes and completion markers | First group's branch |
| Third | Next group's changes and completion markers | Second group's branch |

The request authorizes the orchestrator to create group branches, commit accepted
changes, push them, and create or update the corresponding PRs. Each group must
pass review and be published before the next group starts. PR descriptions
explain the group's change, validation, and dependency on the preceding PR.
Previously completed groups are not retroactively split into PRs.

Publication is tracked separately from code acceptance. A failed push or PR
creation resumes from that checkpoint instead of reimplementing accepted work.
Existing PRs are reconciled before retries, including when OpenSpec already
reports that every task is complete.

If a later check finds a defect in an earlier group, the repair goes through
review on that group's branch and updates its existing PR. Updated parent changes
are propagated through the stack and affected checks rerun. The run finishes
with PR URLs in dependency order and the topmost PR branch checked out, so
Conductor can display it. See [stacked PR details](references/stacked-prs.md).

## Blockers and resuming

The orchestrator keeps a run record in ignored scratch space or a temporary
directory, including group assignments, worker IDs, review findings, validation,
and acceptance. Stacked mode also records branches, commits, and PRs.

Resume the same conversation and ask it to continue the same change. It reconciles
the record with the current files, tasks, and agents, continues an unfinished
group's worker when possible, and uses a replacement for that group if the
worker session was lost. Preserve the run record when moving between sessions.

Missing prerequisites, unclear requirements, unavailable validation, and runtime
limits may block progress. The orchestrator reports the specific issue and leaves
the affected group unaccepted rather than skipping it or claiming completion.

## Tests and coverage

From the repository root, run:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The suite uses Python's standard library and Git. It runs the 16 implementation
tests preserved from the original evaluations and local harness checks for fixture
setup, file preservation, stacked PRs, and completed-run verification. The same
command runs in [CI](../../.github/workflows/tests.yml) on Python 3.9 and 3.13.

The historical real-agent runs exercised sequential workers, parent review,
partially completed groups, stacked publication, and a completed-run resume.
Neither required a repair round. Same-worker repairs, recovery after publication
failure, restacking after repairs, and a Claude-hosted run were not exercised.
The runtime exposed requested model parameters but not effective-model metadata;
the mock PR service provided no remote CI or human review.

See [tests and evaluation instructions](../../tests/README.md) to rerun the
scenarios with real workers and inspect their records. Offline CI does not invoke
an LLM or prove an agent follows the orchestration instructions.

## Files

- [SKILL.md](SKILL.md): instructions loaded by the agent.
- [references/runtimes.md](references/runtimes.md): native worker selection and continuation.
- [references/stacked-prs.md](references/stacked-prs.md): optional publication and stack recovery.

[Back to the skill index](../../README.md) · [MIT license](../../LICENSE)
