#!/usr/bin/env bash
# The odd arm's own check, unchanged: the pinned `odd gate --recompute --base main` in P (arms/odd/post.sh).
exec bash "$(dirname "$0")/../odd/post.sh"
