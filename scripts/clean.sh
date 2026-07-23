#!/usr/bin/env bash
set -euo pipefail

echo "Cleaning build artifacts..."

rm -rf apps/mini-app/dist
rm -rf apps/mini-app/node_modules
rm -rf apps/api/dist
rm -rf apps/api/__pycache__
rm -rf apps/bot/dist
rm -rf apps/bot/__pycache__
rm -rf apps/worker/dist
rm -rf apps/worker/__pycache__

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo "Clean complete."
