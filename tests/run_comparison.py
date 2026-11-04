#!/usr/bin/env python3
"""Run one prepared comparison exactly once, starting from its fixture baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import compare


def assert_fresh(root):
    metadata = json.loads((root / 'evaluation.json').read_text())
    repo = root / 'repo'
    if any((root / name).exists() for name in ('result.json', 'run.json', 'stderr.txt')):
        raise ValueError('run already started; prepare a new directory')
    if compare.git(repo, 'rev-parse', 'HEAD') != metadata['baseline']:
        raise ValueError('repository is no longer at its prepared baseline')
    if compare.git(repo, 'status', '--porcelain'):
        raise ValueError('repository contains changes')
    if compare.git(repo, 'for-each-ref', '--format=%(refname)', 'refs/heads').splitlines() != ['refs/heads/main']:
        raise ValueError('repository already contains layer branches')
    return metadata


def run(directory, executable='claude', budget=2.0):
    root = Path(directory).resolve()
    metadata = assert_fresh(root)
    request = (root / 'REQUEST.txt').read_text()
    skill = Path(metadata['skill']).read_bytes() if metadata['skill'] else b''
    audit = {'baseline': metadata['baseline'], 'fresh': True,
             'request_sha256': hashlib.sha256(request.encode()).hexdigest(),
             'skill_sha256': hashlib.sha256(skill).hexdigest() if skill else None,
             'model': metadata['model'], 'effort': 'medium', 'budget_usd': budget}
    started = time.monotonic()
    with (root / 'run.json').open('x') as stream:
        json.dump(audit, stream, indent=2)
    args = [executable, '-p', request, '--model', metadata['model'], '--effort', 'medium',
            '--output-format', 'json', '--permission-mode', 'acceptEdits',
            '--max-budget-usd', str(budget),
            '--allowedTools', 'Bash', 'Read', 'Edit', 'Write', 'Glob', 'Grep', 'Skill',
            '--disallowedTools', 'Agent', 'Workflow']
    with (root / 'result.json').open('x') as output, (root / 'stderr.txt').open('x') as errors:
        completed = subprocess.run(args, cwd=root / 'repo', stdout=output, stderr=errors)
    audit['exit_code'] = completed.returncode
    audit['minutes'] = (time.monotonic() - started) / 60
    (root / 'minutes.txt').write_text(str(audit['minutes']) + '\n')
    try:
        result = json.loads((root / 'result.json').read_text())
        audit.update({k: result.get(k) for k in ('session_id', 'num_turns', 'usage', 'total_cost_usd', 'is_error', 'subtype', 'terminal_reason', 'api_error_status', 'api_error')})
    except ValueError:
        audit['invalid_result'] = True
    (root / 'run.json').write_text(json.dumps(audit, indent=2) + '\n')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--budget', type=float, default=2.0)
    args = parser.parse_args()
    print(json.dumps(run(args.directory, budget=args.budget), indent=2))
