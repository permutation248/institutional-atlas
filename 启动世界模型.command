#!/usr/bin/env bash
set -euo pipefail
atlas_root="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$atlas_root"
if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -c 'import yaml' >/dev/null 2>&1; then
  ./scripts/dev.sh setup
fi
exec ./scripts/dev.sh open "$@"
