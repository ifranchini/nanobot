#!/bin/sh
# Docker entrypoint: sync builtin skills with scripts into the workspace,
# then exec the nanobot command.
#
# Builtin skills live at /app/nanobot/skills/ (baked into image).
# The workspace at /root/.nanobot/workspace/skills/ is where the agent
# can actually execute scripts (restrictToWorkspace=true).
#
# This copies any builtin skill that has a scripts/ directory into the
# workspace, without overwriting user-created workspace skills.

BUILTIN="/app/nanobot/skills"
WORKSPACE="/root/.nanobot/workspace/skills"

if [ -d "$BUILTIN" ]; then
    mkdir -p "$WORKSPACE"
    for skill_dir in "$BUILTIN"/*/; do
        skill_name=$(basename "$skill_dir")
        # Only sync skills that have bundled scripts
        if [ -d "$skill_dir/scripts" ]; then
            # Skip if workspace already has a user-modified version
            # (user version takes priority if SKILL.md is newer)
            ws_skill="$WORKSPACE/$skill_name/SKILL.md"
            bi_skill="$skill_dir/SKILL.md"
            if [ -f "$ws_skill" ] && [ "$ws_skill" -nt "$bi_skill" ]; then
                continue
            fi
            # Sync the skill
            mkdir -p "$WORKSPACE/$skill_name"
            cp -r "$skill_dir"/* "$WORKSPACE/$skill_name/"
        fi
    done
fi

exec nanobot "$@"
