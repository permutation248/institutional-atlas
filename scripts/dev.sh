#!/usr/bin/env bash
# Local-only development. This script never commits, pushes or deploys.
set -euo pipefail

atlas_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$atlas_root"
atlas_python="$atlas_root/.venv/bin/python"
atlas_command="${1:-help}"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev.sh <command> [port]
  setup        Create .venv and install requirements inside it
  check        Build, run Python tests, and run JS tests if Node 20+ is installed
  build        Rebuild dist/index.html, atlas.json and coverage.json
  serve [port] Rebuild and serve dist on 127.0.0.1 (default 8765)
  open [port]  Serve and open the local explorer in your browser

Press Ctrl+C in the server terminal to stop it. No Git sync is performed.
EOF
}

require_environment() {
  if [[ ! -x "$atlas_python" ]] || ! "$atlas_python" -c 'import yaml' >/dev/null 2>&1; then
    echo 'Local Python environment is missing. Run: ./scripts/dev.sh setup' >&2
    exit 1
  fi
}

case "$atlas_command" in
  setup)
    if [[ ! -x "$atlas_python" ]]; then
      python3 -m venv "$atlas_root/.venv"
    fi
    "$atlas_python" -m pip install -r "$atlas_root/requirements.txt"
    ;;
  check)
    require_environment
    for atlas_script in scripts/dev.sh 启动图谱.command 启动视觉模型.command 启动世界模型.command; do
      bash -n "$atlas_script"
    done
    "$atlas_python" scripts/build.py
    "$atlas_python" -m unittest discover -s tests -v
    if command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'; then
      node --check web/app.js
      node --test tests/frontend_contract.test.cjs
    else
      echo 'JavaScript tests skipped: Node.js 20+ is optional for local development. Python build/tests passed.'
    fi
    ;;
  build)
    require_environment
    "$atlas_python" scripts/build.py
    ;;
  serve|open)
    require_environment
    if [[ "$#" -gt 2 ]]; then usage >&2; exit 2; fi
    atlas_port="${2:-${ATLAS_PORT:-8765}}"
    "$atlas_python" scripts/build.py
    if [[ "$atlas_command" == open ]]; then
      exec "$atlas_python" scripts/serve.py --port "$atlas_port" --open
    fi
    exec "$atlas_python" scripts/serve.py --port "$atlas_port"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
