#!/bin/sh
set -eu

mode="$1"

case "$mode" in
  baseline)
    exec python /opt/fencepost/batch_driver.py baseline
    ;;
  mutant)
    python -m compileall -q . || exit 10
    pytest --collect-only -q -p no:cacheprovider || exit 11
    exec pytest -q -p no:cacheprovider --junitxml=/tmp/fencepost-junit.xml
    ;;
  batch)
    exec python /opt/fencepost/batch_driver.py batch /input/manifest.json
    ;;
  triage-session)
    trap 'exit 0' TERM INT
    while :; do
      sleep 3600 &
      wait "$!"
    done
    ;;
  *)
    echo "unknown runner mode: $mode" >&2
    exit 64
    ;;
esac
