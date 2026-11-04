# Skills

Reusable skills for Codex and Claude Code. Each skill lives in its own directory
under `skills/`, with installation instructions, examples, and agent guidance.

## Skill index

| Skill | Short version |
| --- | --- |
| [OpenSpec Stack Apply](skills/openspec-stack-apply/README.md) | Apply an OpenSpec change top to bottom in one session with one `gh stack` layer per task group, then publish PRs ready for review and batch review feedback. |
| [Stacked PR Feedback](skills/stacked-pr-feedback/README.md) | Triage review feedback across a PR stack, fix each issue on the PR that introduced it, restack, and reply. Works on any stack; optional local AI review. |

## Quick example

In the project containing your OpenSpec change:

```text
/openspec-stack-apply <change-name>
```

It builds one tested PR per task group, opens them ready for review,
and handles confirmed findings across the stack. Local LLM pre-review is
opt-in. Bring findings from your human or ChatGPT web review back with
`/stacked-pr-feedback auto` for batch fixes, or omit `auto` to approve the plan
first. Use `$` instead of `/` in Codex.

## Installation

Clone this repository, then from its root link each skill into both global
skill directories:

```sh
for skill in openspec-stack-apply stacked-pr-feedback; do
  for skill_home in "$HOME/.codex/skills" "$HOME/.claude/skills"; do
    mkdir -p "$skill_home"
    target="$skill_home/$skill"
    if [ -e "$target" ] || [ -L "$target" ]; then
      printf 'Already installed; leaving in place: %s\n' "$target"
    else
      ln -s "$PWD/skills/$skill" "$target"
    fi
  done
done
```

Keep the checkout at a stable path; moving it breaks the links. Alternatively,
copy each skill directory, including its `scripts/`. Start a new agent session
if a skill does not appear.

## Tests

Run the offline suite with Python 3.9+ and Git:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

[GitHub Actions](.github/workflows/tests.yml) runs this suite on pushes, pull
requests, and manual dispatches using Python 3.9 and 3.13. It needs no model
credentials. [Evaluation instructions](tests/README.md) explain how to compare
ways of applying a change and measure review precision with real agents.

## License

[MIT](LICENSE).
