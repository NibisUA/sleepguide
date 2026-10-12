#!/usr/bin/env bash
# Atomic custom-format backup; optional copy to a preconfigured rclone crypt remote.
set -euo pipefail
umask 077
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
backup_dir="${BACKUP_DIR:-$project_dir/backups}"
retention="${BACKUP_RETENTION_DAYS:-14}"
[[ "$retention" =~ ^[0-9]+$ && "$retention" -ge 1 ]] || { echo 'Invalid retention' >&2; exit 1; }
mkdir -p -- "$backup_dir"
backup_dir="$(cd "$backup_dir" && pwd)"
[[ "$backup_dir" != / ]] || { echo 'Refusing filesystem root' >&2; exit 1; }
dc=(docker compose --env-file "$project_dir/.env.prod" -f "$project_dir/docker-compose.prod.yml")
name="sleepguide_$(date -u +%Y%m%dT%H%M%SZ)_$$.dump"
temporary="$(mktemp "$backup_dir/.partial.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
"${dc[@]}" exec -T db pg_dump -U sleepguide -d sleepguide --format=custom --no-owner --no-acl > "$temporary"
"${dc[@]}" exec -T db pg_restore --list < "$temporary" > /dev/null
mv -- "$temporary" "$backup_dir/$name"
(cd "$backup_dir" && sha256sum "$name" > "$name.sha256")
if [[ -n "${BACKUP_REMOTE:-}" ]]; then
  command -v rclone > /dev/null || { echo 'rclone is required for off-server copies' >&2; exit 1; }
  # The owner configures this as an encrypted crypt remote before enabling upload.
  rclone copyto "$backup_dir/$name" "${BACKUP_REMOTE%/}/$name"
  rclone copyto "$backup_dir/$name.sha256" "${BACKUP_REMOTE%/}/$name.sha256"
fi
# Prune only our regular dump files and matching checksums, after a successful copy.
while IFS= read -r -d '' expired; do
  rm -f -- "$expired" "$expired.sha256"
done < <(find "$backup_dir" -maxdepth 1 -type f -name 'sleepguide_*.dump' -mtime "+$retention" -print0)
printf 'Verified backup: %s\n' "$name"
