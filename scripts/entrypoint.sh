#!/bin/sh
# Docker entrypoint: sync builtin skills with scripts into the workspace,
# then exec the nanobot command.
#
# Skills source priority:
#   1. /repo/nanobot/skills/ (git repo volume mount — latest code)
#   2. /app/nanobot/skills/  (baked into image — fallback)
#
# The workspace at /root/.nanobot/workspace/skills/ is where the agent
# can actually execute scripts (restrictToWorkspace=true).
#
# This always syncs skills that have a scripts/ directory into workspace,
# ensuring quick deploys (restart without rebuild) pick up latest code.

if [ -d "/repo/nanobot/skills" ]; then
    BUILTIN="/repo/nanobot/skills"
else
    BUILTIN="/app/nanobot/skills"
fi

WORKSPACE="/root/.nanobot/workspace/skills"

if [ -d "$BUILTIN" ]; then
    mkdir -p "$WORKSPACE"
    for skill_dir in "$BUILTIN"/*/; do
        skill_name=$(basename "$skill_dir")
        # Only sync skills that have bundled scripts
        if [ -d "$skill_dir/scripts" ]; then
            mkdir -p "$WORKSPACE/$skill_name"
            cp -r "$skill_dir"/* "$WORKSPACE/$skill_name/"
        fi
    done
fi

exec nanobot "$@"
