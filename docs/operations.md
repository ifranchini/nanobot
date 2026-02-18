# Operations Runbook

## Deploy Changes

✅ **Safe to run directly** (standard deploy cycle)

### Full deploy (code + Dockerfile changes)

**ALWAYS: test -> commit -> deploy**

```bash
# 1. Run tests (must pass before committing)
uv run pytest -v

# 2. Push local changes to stable
git checkout stable && git reset --hard my-modifications && git push --force-with-lease && git checkout my-modifications

# 3. Pull on VPS
ssh puma-vps "sudo -u nanobot bash -c 'cd /home/nanobot/nanobot && git pull origin stable'"

# 4. Build and restart container
ssh puma-vps "sudo bash -c 'cd /home/nanobot/nanobot && docker build -t nanobot . && docker stop nanobot && docker rm nanobot && docker run -d --name nanobot --restart unless-stopped --env-file /home/nanobot/nanobot/.env -p 18790:18790 -v /home/nanobot/.nanobot:/root/.nanobot -v /home/nanobot/nanobot:/repo nanobot gateway'"

# 5. Start fresh Telegram session
ssh puma-vps "sudo docker exec nanobot nanobot agent --session telegram:6682587663 -m '/new'"
```

### Quick deploy (skill/config changes only — no Docker rebuild needed)

**ALWAYS: test -> commit -> deploy**

```bash
# 1. Run tests (must pass before committing)
uv run pytest -v

# 2. Push local changes to stable
git checkout stable && git reset --hard my-modifications && git push --force-with-lease && git checkout my-modifications
ssh puma-vps "sudo -u nanobot bash -c 'cd /home/nanobot/nanobot && git pull origin stable'"
ssh puma-vps "sudo docker restart nanobot"
ssh puma-vps "sudo docker exec nanobot nanobot agent --session telegram:6682587663 -m '/new'"
```

## View Logs

✅ **Safe to run directly**

```bash
# Recent logs
ssh puma-vps "cd /home/nanobot/nanobot && docker-compose logs --tail=100"

# Follow logs
ssh puma-vps "cd /home/nanobot/nanobot && docker-compose logs -f"

# Specific service
ssh puma-vps "cd /home/nanobot/nanobot && docker-compose logs nanobot --tail=50"
```

## Check Status

✅ **Safe to run directly**

```bash
# Container status
ssh puma-vps "docker ps"

# Disk usage
ssh puma-vps "df -h"

# Memory
ssh puma-vps "free -h"
```

## Check Cron Jobs

✅ **Safe to run directly**

```bash
# List scheduled jobs
ssh puma-vps "atq"

# View job details
ssh puma-vps "at -c <job_id>"
```

## Clear Stuck Cron Jobs

⚠️ **Ask user to confirm before running**

```bash
# Remove specific job
ssh puma-vps "atrm <job_id>"

# Clear all (dangerous)
ssh puma-vps "for job in \$(atq | cut -f1); do atrm \$job; done"
```

## Restart Services

✅ **Safe to run directly**

```bash
ssh puma-vps "sudo docker restart nanobot"
```

## Sync with Upstream

⚠️ **Ask user to confirm before running**

Normally handled by GitHub Action (daily at 06:00 UTC). Sends Telegram alert on failure.

### When you get a "Sync Failed" Telegram alert

Just tell Claude: **"resolve sync conflict"** — this runbook has all the context needed.

### Resolve sync conflict (Claude runs this)

```bash
# 1. Fetch latest upstream
git fetch upstream
git fetch origin

# 2. Update main to match upstream
git checkout main
git reset --hard upstream/main
git push origin main --force

# 3. Start interactive rebase
git checkout my-modifications
git rebase main
# If conflicts: git shows which files conflict.
# For each conflict:
#   - Open the file, look for <<<<<<< / ======= / >>>>>>> markers
#   - Keep OUR custom changes (HEAD), integrate any upstream changes we need
#   - git add <resolved-file>
#   - git rebase --continue
# Repeat until rebase completes.

# 4. Verify no commits were lost
git log --oneline main..my-modifications
# Compare count to what's expected. If commits are missing, investigate.

# 5. Run tests before pushing
uv run pytest -v

# 6. Push and update stable
git push origin my-modifications --force-with-lease
git checkout stable && git reset --hard my-modifications && git push --force-with-lease
git checkout my-modifications
```

### Key principles for conflict resolution

- **Always keep our custom changes** — upstream doesn't know about our modifications
- **Files we commonly customize** (likely to conflict): `commands.py`, `loop.py`, `web.py`
- **After resolving**: run tests, verify commit count, then push
- **If unsure about a conflict**: keep both versions and test

## View Config

✅ **Safe to run directly**

```bash
ssh puma-vps "cat /home/nanobot/.nanobot/config.json"
```

## View Memory

✅ **Safe to run directly**

```bash
ssh puma-vps "cat /home/nanobot/.nanobot/workspace/MEMORY.md"
ssh puma-vps "tail -50 /home/nanobot/.nanobot/workspace/HISTORY.md"
```

## Troubleshooting

### Bot not responding
1. Check container is running: `docker ps`
2. Check logs for errors: `docker-compose logs --tail=100`
3. Verify config has valid API keys

### Reminders not firing
1. Check `atd` service: `systemctl status atd`
2. List pending jobs: `atq`
3. Verify job content: `at -c <job_id>`

### Memory not persisting
1. Check workspace permissions
2. Verify MEMORY.md exists and is writable
3. Check Docker volume mounts

### Channel disconnected
1. Check channel-specific logs
2. Verify API tokens in config
3. Restart gateway: `docker-compose restart`
