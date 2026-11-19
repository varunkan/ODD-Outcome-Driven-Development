#!/usr/bin/env bash
# One session does the whole request as in the odd arm; then `odd second`, and a settling session if they differ.
exec python3 "$ARM_HELPER" odd second
