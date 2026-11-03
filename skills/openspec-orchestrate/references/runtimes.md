# Worker lifecycle by runtime

Read the section for the runtime you are actually using. Tool schemas in the
current session take precedence over examples here. A model name in a prompt
does not set the worker's model: use an explicit tool parameter or a verified
agent configuration. Keep selection consistent across repair turns.

## Codex

Use the available native spawn, follow-up/input, wait, and close controls.
Choose an agent with implementation tools. If spawning exposes `model`, set it
to the user's value. In runtimes exposing `fork_turns`, use `"none"` when a
model override requires it; provide the full assignment explicitly.

For the collaboration tool family, `spawn_agent` creates the worker,
`followup_task` resumes an idle worker, and `send_message` only steers a running
one. Use the wait/status tools to confirm the turn is finished. In other Codex
runtimes these operations may be named `send_input`, `resume_agent`, or
`wait_agent`; use only tools and arguments that actually exist. A closed agent
may need resuming before sending input.

If per-spawn model selection is absent, use an already configured custom agent
only after checking that it selects the requested model. Custom agent model
settings can override spawn defaults. If neither route can select it, report
the setup needed; do not invent a `model` argument, edit global defaults, or
quietly fall back to the parent's model.

See the official [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
for the installed client's configuration options.

## Claude Code

Use an implementation-capable, resumable agent such as `general-purpose`, via
the available `Agent` tool (called `Task` in some versions). The live schema
determines accepted model aliases. For an exact model ID unsupported by that
parameter, use a loaded custom agent configured with that exact ID. Do not
replace the exact ID with a family alias.

Save the returned agent ID. Continue it with `SendMessage` addressed to that ID
on versions exposing that mechanism, or the `resume` parameter on versions
whose Agent/Task tool supports it. Wait for each continued turn to finish.
Keep the requested model on follow-ups where the schema supports selection.
A new invocation without continuation creates a fresh worker for the next
group. Do not use a one-shot exploration or planning agent for implementation.

If an exact model needs a custom agent that is not loaded, explain the required
configuration or reload. Check runtime warnings or exposed metadata for model
substitutions. Do not override the parent model or permission settings.

Keep this skill in the parent conversation; do not set `context: fork` or a
fixed `model` in its frontmatter. The parent must remain available to review
and manage successive workers.

See [Claude Code subagents](https://code.claude.com/docs/en/sub-agents) for model
selection and continuation in the installed version.

## Capability boundary

This skill uses the current host's native agents. It does not promise that
Codex can run an Anthropic model, or that Claude Code can run an OpenAI model.
If the requested provider/model is unavailable, report that before delegation.
Do not replace native workers with nested CLI sessions or another provider
without an explicit user request for that execution method.
