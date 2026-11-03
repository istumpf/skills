"""Run the original workers' 16 implementation tests in isolated processes."""

from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unittest


class OriginalImplementationTests(unittest.TestCase):
    def run_original_tests(self, case):
        source = Path(__file__).resolve().parent / "outputs" / case
        with tempfile.TemporaryDirectory(prefix="openspec-original-tests-") as temp:
            for path in source.glob("*.py"):
                shutil.copy2(path, Path(temp) / path.name)
            subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"],
                           cwd=temp, check=True)

    def test_default_original_implementation(self):
        self.run_original_tests("default")

    def test_stacked_original_implementation(self):
        self.run_original_tests("stacked-prs")
