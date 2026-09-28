#!/bin/sh
set -eu
mkdir -p /logs/verifier
trap 'printf "0\n" > /logs/verifier/reward.txt' EXIT
if pytest -q --ctrf=/logs/verifier/ctrf.json /tests/test_verify.py; then
  printf "1\n" > /logs/verifier/reward.txt
  trap - EXIT
else
  printf "0\n" > /logs/verifier/reward.txt
  trap - EXIT
fi
