#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
dc=(docker compose --env-file .env.prod -f docker-compose.prod.yml)
"${dc[@]}" config --quiet
"${dc[@]}" ps
"${dc[@]}" exec -T backend python -c \
  'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read().decode())'
"${dc[@]}" exec -T backend alembic current
echo 'Review docs/RELEASE.md and record the external/device checks before inviting beta users.'
