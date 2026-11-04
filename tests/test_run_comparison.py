"""Prevent accidental measurement of resumed implementations as fresh builds."""
import tempfile
from pathlib import Path
import unittest

import compare
import run_comparison


class FreshRunTests(unittest.TestCase):
    def test_rejects_modified_or_already_started_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = compare.prepare('single', Path(temp) / 'run', 'test-model', case_name='warehouse')
            self.assertEqual(run_comparison.assert_fresh(root)['arm'], 'single')
            path = root / 'repo/warehouse.py'
            original = path.read_text()
            path.write_text(original + '\n# changed\n')
            with self.assertRaisesRegex(ValueError, 'changes'):
                run_comparison.assert_fresh(root)
            path.write_text(original)
            compare.git(root / 'repo', 'branch', 'warehouse-ledger/1-state')
            with self.assertRaisesRegex(ValueError, 'branches'):
                run_comparison.assert_fresh(root)
            compare.git(root / 'repo', 'branch', '-D', 'warehouse-ledger/1-state')
            (root / 'result.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'already started'):
                run_comparison.assert_fresh(root)

    def test_failed_agent_session_is_not_an_implementation_score(self):
        with tempfile.TemporaryDirectory() as temp:
            root = compare.prepare('single', Path(temp) / 'run', 'test-model', case_name='warehouse')
            for audit in ('{}', '{"exit_code": 1}', '{"exit_code": 0, "is_error": true}'):
                (root / 'run.json').write_text(audit)
                with self.assertRaisesRegex(ValueError, 'failed agent run'):
                    compare.score(root, validate_spec=False)
            self.assertFalse((root / 'score.json').exists())
