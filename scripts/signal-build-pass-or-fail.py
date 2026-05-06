"""
Exit non-zero if any JUnit XML report contains failures or errors.

Usage:
    python scripts/signal-build-pass-or-fail.py <working-dir> <suite1> [suite2 ...]
"""

import re
import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: python signal-build-pass-or-fail.py <working-dir> <suite> [suite ...]")
        sys.exit(0)

    working_dir = sys.argv[1]
    suites = sys.argv[2:]

    report_paths = [
        f"{working_dir}/functional-test-reports/{suite}" for suite in suites
    ]

    pattern = r'(errors|failures)="([1-9][0-9]*)"'

    for path in report_paths:
        try:
            with open(path, "r") as f:
                content = f.read()
            if re.search(pattern, content):
                print(f"Non-passing tests found in {path}. Exiting with status 1.")
                sys.exit(1)
        except FileNotFoundError:
            print(f"WARNING: report not found: {path}")


if __name__ == "__main__":
    main()
