# Launch kit

| file | what it is |
|---|---|
| [`demo.sh`](demo.sh) | The 60-second demo: an agent's test that asserts nothing is refused, then a real one passes, then CI recomputes. Real output, run by the test suite so it cannot go stale. Record it with `asciinema rec -c "bash launch/demo.sh"`. |
| [`../site/index.html`](../site/index.html) | The one-page site. One file, no scripts, light and dark, checked at phone width. Published by `.github/workflows/pages.yml`. |
| [`RELEASE-NOTES-v0.4.0.md`](RELEASE-NOTES-v0.4.0.md) | Paste into the GitHub release. |
| [`POST.md`](POST.md) | The launch post: why, what, what is not claimed. |
| [`ANNOUNCE.md`](ANNOUNCE.md) | Show HN, Reddit, X and LinkedIn text, and lists to submit to. |

## Order, and who does what

1. **Owner:** merge the pull request into `main`.
2. **Owner:** Settings, Pages, Source: GitHub Actions. The site deploys from `site/`.
3. **Owner, once:** on pypi.org, add a pending trusted publisher (project `odd-tool`, owner `varunkan`, repository
   `ODD-Outcome-Driven-Development`, workflow `release.yml`, environment `pypi`); in the repository, create the
   environment `pypi`.
4. **Owner:** create the release `v0.4.0` on GitHub with the release notes, ticking "Publish this Action to the GitHub
   Marketplace". The tag publishes the package to PyPI.
5. Check: `pipx install odd-tool && odd --version` prints 0.4.0; `bash launch/demo.sh` passes; the site loads.
6. Post `POST.md` and the announcements. Watch issues for the first week; every reproduced report becomes a test.
7. When the comparison has run: add its results page, put the headline figure and its spread on the site and in the
   README, and post the result, whatever it shows.

## What the launch must not say

No multiplier, no "beats", no speed or cost figure until the comparison has run. "Works with Cursor, Copilot, ..."
means they read AGENTS.md by their documentation; only Claude Code has been run with it.
