#!/usr/bin/env bash
# odd-cascade plus a blind second proof: a fresh session writes its own test from the ticket alone, no coding attempt
# sees it, and the arm says DONE only when the result passes both proofs (NOTES.md).
# ARM_TICKET_END: the first words of prompt.md after {ticket}, so the blind author gets the ticket and nothing else.
ARM_TICKET_END='Work as AGENTS.md describes' exec python3 "$ARM_HELPER" odd dual
