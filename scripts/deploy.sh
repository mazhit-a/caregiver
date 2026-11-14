#!/usr/bin/env bash
# Runs ON THE VPS (called by the CD workflow over SSH): bring /opt/kelper to a commit and restart.
# On failure it puts the previous commit back, so a bad push does not leave the site down.
set -euo pipefail

TARGET="${1:?usage: deploy.sh <commit-sha>}"
cd /opt/kelper
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

up() {
  git checkout --quiet "$1"
  "${COMPOSE[@]}" up --build -d --wait --wait-timeout 180
}

PREVIOUS="$(git rev-parse HEAD)"
git fetch --quiet origin main

echo "Deploying ${TARGET} (previous ${PREVIOUS})"
if up "${TARGET}"; then
  docker image prune -f >/dev/null
  echo "Deployed ${TARGET}"
else
  echo "Deploy failed, rolling back to ${PREVIOUS}" >&2
  up "${PREVIOUS}" || echo "Rollback failed too: check 'docker compose logs'" >&2
  exit 1
fi
