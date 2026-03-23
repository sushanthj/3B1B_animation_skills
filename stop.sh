#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_DIR="$REPO_DIR/setup"

echo "Stopping containers..."
docker compose -f "$SETUP_DIR/docker-compose.yml" down

echo "Cleaning up __pycache__..."
rm -rf "$REPO_DIR/__pycache__"
find "$REPO_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$REPO_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

echo "Done."
