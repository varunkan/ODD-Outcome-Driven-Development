#!/usr/bin/env bash
# The 60-second demo: an agent says "done" with a test that cannot fail, and odd refuses it; then a real test
# passes. Runs in a throwaway directory and prints only what a viewer needs. Usage: bash launch/demo.sh
set -euo pipefail
ODD_PY="$(cd "$(dirname "$0")/.." && pwd)/odd.py"
d="$(mktemp -d)"; trap 'rm -rf "$d"' EXIT
cd "$d"
say() { printf '\n\033[1m# %s\033[0m\n' "$*"; }
run() { printf '$ %s\n' "$1"; shift; "$@" 2>&1 | sed 's#'"$d"'#.#g' || true; }   # run "<as shown>" cmd args...

git init -q -b main && git config user.email demo@example.com && git config user.name demo
mkdir -p billing tests && printf '__pycache__/\n' > .gitignore
cat > billing/split.py <<'PY'
def split(total_cents, ways):
    return [total_cents // ways] * ways
PY
git add -A && git commit -qm "a bill splitter that loses cents"
python3 "$ODD_PY" init >/dev/null && git add -A && git commit -qm "adopt odd" && git switch -qc fix-split
odd() { python3 .odd/odd.py "$@"; }

say "The ticket: a bill of 100.00 split three ways loses a cent. State the outcome first."
run 'odd new split "A cashier who splits a bill three ways sees three amounts that add up to the bill." --proof "python3 -m unittest -q tests.test_split" --in "billing/**"' \
  odd new split "A cashier who splits a bill three ways sees three amounts that add up to the bill." \
  --proof "python3 -m unittest -q tests.test_split" --in "billing/**"

say "The agent writes a test that asserts nothing, 'fixes' the code, and says done."
cat > tests/test_split.py <<'PY'
import unittest
from billing.split import split

class T(unittest.TestCase):
    def test_split(self):
        self.assertEqual(len(split(10000, 3)), 3)
PY
cat > billing/split.py <<'PY'
def split(total_cents, ways):
    base = total_cents // ways
    return [base] * ways  # tidied up
PY
run 'odd done split' odd done split

say "odd took the change out and the test still passed, so it proves nothing. Now a real test and a real fix."
cat > tests/test_split.py <<'PY'
import unittest
from billing.split import split

class T(unittest.TestCase):
    def test_parts_add_up_to_the_bill(self):
        self.assertEqual(sum(split(10000, 3)), 10000)
PY
cat > billing/split.py <<'PY'
def split(total_cents, ways):
    base, extra = divmod(total_cents, ways)
    return [base + 1 if i < extra else base for i in range(ways)]
PY
run 'odd done split' odd done split

say "In CI the same verdict is recomputed from the code; nothing the agent recorded is trusted."
git add -A && git commit -qm "split adds up"
run 'odd gate --recompute --base main' odd gate --recompute --base main
