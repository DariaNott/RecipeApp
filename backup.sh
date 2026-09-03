#!/bin/bash

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKUP_DIR="$PROJECT_DIR/backups"

# Create dir if it doesn't exist
mkdir -p "$BACKUP_DIR"

DATE=$(date +'%Y-%m-%d_%H-%M')
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql"

# Create db dump from Docker container pi-postgres
docker exec pi-postgres pg_dump -U postgres postgres > "$BACKUP_FILE"


# Keep only 3 recent .sql files, delete the rest
ls -1t "$BACKUP_DIR"/*.sql 2>/dev/null | tail -n +4 | xargs -I {} rm -- {}

echo "Backup created successfully: $BACKUP_FILE"
