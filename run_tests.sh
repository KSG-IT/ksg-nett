#!/usr/bin/env bash
# Run the test suite with a coverage report over the project apps.
# Plain `make test` is what CI runs; this is for local coverage inspection.
set -euo pipefail

MODULES=(
  admissions api bar_tab chat common economy external handbook
  internal login organization quotes schedules sensors summaries users
)

COV_ARGS=()
for module in "${MODULES[@]}"; do
  COV_ARGS+=("--cov=${module}")
done

poetry run pytest "${COV_ARGS[@]}" --cov-report=term-missing
