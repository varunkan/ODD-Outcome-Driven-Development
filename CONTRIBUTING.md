# Contributing

odd is one Python file (`odd.py`, standard library only, Python 3.8 and later) with its tests in `tests/`, and a
benchmark harness in `bench/`.

## Before you open a pull request

```bash
python3 -m unittest discover -s tests          # the tool
python3 tests/proof_index.py --check           # docs/PROOF.md lists every test class exactly once
python3 -m unittest discover -s bench/tests    # the harness
python3 bench/validate.py                      # the benchmark tasks
```

CI runs the same four on Python 3.8 and 3.13, on Linux and macOS.

## What a change needs

- **A test written first and seen failing.** Then break your own change on purpose and see the test notice; a
  check nobody has seen fail is not trusted here.
- **No second copy of existing code.** Find the function that does the nearest thing and extend it.
- **The design and the backlog in the same change.** Behaviour is described in `DESIGN.md`; why it exists, with its
  evidence, in `BACKLOG.md`. A new test class goes into one theme in `tests/proof_index.py`.
- **No model names in the tool.** odd calls no model; agents are commands the user configures.

## Adding a check

A check that can fail someone's work has to earn it ([DESIGN 3r](DESIGN.md)). It enters as report only. It may fail
work once it has been replayed, with no model, on kept programs from two different kinds of task without one false
alarm, has found a real defect on a task it was not built on, and has run one model round with its targets fixed
beforehand. One false alarm on correct work later puts it back to report only. It adds nothing to the method text:
its failure message carries the instruction and a way out.

## Evidence

Measurements live in `docs/evidence/`, each with its data. The rules they follow:

- success numbers are written down before a run, and the page says whether they were met;
- a result that did not go odd's way stays on the page;
- small samples are called hints, with the counts shown;
- nothing private goes in: no names, addresses or project details from anyone's repository.

## Reporting a bug

Open an issue with the command you ran, its output, and the smallest repository that shows it. For anything that
lets a change pass the gate when it should not, see [SECURITY.md](SECURITY.md) instead.
