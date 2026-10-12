#!/usr/bin/env bash
# Restore ONLY into a new disposable DB; never overwrite the application DB.
set -euo pipefail
umask 077
[[ $# -eq 1 ]] || { echo 'Usage: restore-drill.sh /absolute/path/backup.dump' >&2; exit 1; }
dump="$(realpath "$1")"
[[ -f "$dump" && "$dump" == *.dump ]] || { echo 'Expected a custom .dump backup' >&2; exit 1; }
[[ -f "$dump.sha256" ]] || { echo 'Checksum file is required' >&2; exit 1; }
(cd "$(dirname "$dump")" && sha256sum -c "$(basename "$dump").sha256")
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dc=(docker compose --env-file "$project_dir/.env.prod" -f "$project_dir/docker-compose.prod.yml")
target="sleepguide_restore_$(date -u +%s)_$$_test"
[[ "$target" =~ ^sleepguide_restore_[0-9]+_[0-9]+_test$ ]] || exit 1
created=0
cleanup() { if [[ "$created" == 1 ]]; then "${dc[@]}" exec -T db dropdb -U sleepguide "$target"; fi; }
trap cleanup EXIT
"${dc[@]}" exec -T db createdb -U sleepguide "$target"
created=1
"${dc[@]}" exec -T db pg_restore -U sleepguide -d "$target" --exit-on-error --single-transaction --no-owner --no-acl < "$dump"
"${dc[@]}" exec -T db psql -U sleepguide -d "$target" -v ON_ERROR_STOP=1 -c \
  'SELECT version_num FROM alembic_version; SELECT count(*) FROM users; SELECT count(*) FROM sleep_sessions; SELECT count(*) FROM workouts; SELECT count(*) FROM stress_logs; SELECT count(*) FROM screen_time_daily; SELECT count(*) FROM api_tokens; SELECT count(*) FROM insights; SELECT count(*) FROM exercises; SELECT count(*) FROM exercise_logs;'
printf 'Restore drill passed in disposable database %s\n' "$target"
