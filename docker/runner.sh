#!/bin/sh
set -eu

mode="$1"

case "$mode" in
  baseline)
    set +e
    coverage run --rcfile=/opt/fencepost/coveragerc --data-file=/tmp/.coverage \
      -m pytest -q -p no:cacheprovider
    status=$?
    set -e
    coverage json --rcfile=/opt/fencepost/coveragerc --data-file=/tmp/.coverage \
      -o /out/coverage.json || true
    exit "$status"
    ;;
  mutant)
    python -m compileall -q . || exit 10
    pytest --collect-only -q -p no:cacheprovider || exit 11
    exec pytest -q -p no:cacheprovider --junitxml=/out/junit.xml
    ;;
  batch)
    exec python /opt/fencepost/batch_driver.py \
      /input/manifest.json /out/batch-results.json
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
