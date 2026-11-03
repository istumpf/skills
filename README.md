# Skills

Reusable skills for Codex and Claude Code. Each skill lives in its own directory
under `skills/`, with installation instructions, examples, and agent guidance.

## Skill index

| Skill | Short version |
| --- | --- |
| [OpenSpec Orchestrate](skills/openspec-orchestrate/README.md) | Apply an OpenSpec change one task group at a time, using a fresh worker with your selected model and parent review before acceptance. Optionally publish one stacked PR per group. |

## Quick example

After [installing OpenSpec Orchestrate](skills/openspec-orchestrate/README.md#installation),
invoke it in the project containing your OpenSpec change:

```text
$openspec-orchestrate <change-name> using worker model <model>
```

Use `/openspec-orchestrate` in Claude Code. Append `with one stacked PR per group`
to request a PR stack. See the skill's README for the complete workflow and usage.

## Tests

Run the offline suite with Python 3.9+ and Git:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

[GitHub Actions](.github/workflows/tests.yml) runs this suite on pushes, pull
requests, and manual dispatches using Python 3.9 and 3.13. It needs no model
credentials. [Evaluation instructions](tests/README.md) explain how to rerun
the original scenarios with real agents.

## License

[MIT](LICENSE).
