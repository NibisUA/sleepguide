#!/usr/bin/env bash
# Daily PostgreSQL dump, keeps 14 days. Cron example (crontab -e):
#   0 3 * * * /home/ubuntu/sleepguide/deploy/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p "$HOME/backups"
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T db \
  pg_dump -U sleepguide sleepguide | gzip > "$HOME/backups/sleepguide_$(date +%F).sql.gz"
find "$HOME/backups" -name 'sleepguide_*.sql.gz' -mtime +14 -delete
