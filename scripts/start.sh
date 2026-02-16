#!/bin/bash
set -e
# Load and export env vars
set -a
source /home/nanobot/nanobot/.env
set +a
# Inject into config
envsubst < /home/nanobot/.nanobot/config.template.json > /home/nanobot/.nanobot/config.json
# Stop existing container if running
docker stop nanobot 2>/dev/null || true
docker rm nanobot 2>/dev/null || true
# Run nanobot
docker run -d \
  --name nanobot \
  --restart unless-stopped \
  --env-file /home/nanobot/nanobot/.env \
  -v /home/nanobot/.nanobot:/root/.nanobot \
  -v /home/nanobot/nanobot:/repo \
  -p 18790:18790 \
  nanobot gateway
