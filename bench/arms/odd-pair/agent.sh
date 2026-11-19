#!/usr/bin/env bash
# The odd-race arm's flow with two attempts instead of three (ARM_RACE_N), so passing attempts can be compared.
ARM_RACE_N=2 exec python3 "$ARM_HELPER" odd race
