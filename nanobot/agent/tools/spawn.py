"""Spawn tool for creating background subagents."""

import re
from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager

# Patterns that indicate a delayed/scheduled task (should use cron, not spawn)
_DELAY_PATTERN = re.compile(
    r"\b(sleep|wait)\s+\d|"
    r"\bin\s+\d+\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)\b|"
    r"\bafter\s+\d+\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)\b|"
    r"\b\d+\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)\s*(from now|later)\b",
    re.IGNORECASE,
)


class SpawnTool(Tool):
    """
    Tool to spawn a subagent for background task execution.

    The subagent runs asynchronously and announces its result back
    to the main agent when complete.
    """

    def __init__(self, manager: "SubagentManager"):
        self._manager = manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the origin context for subagent announcements."""
        self._origin_channel = channel
        self._origin_chat_id = chat_id

    @property
    def name(self) -> str:
        return "spawn"

    @property
    def description(self) -> str:
        return (
            "Spawn a subagent to handle a task in the background. "
            "Use this for complex tasks that need parallel tool use (e.g. research). "
            "The subagent will complete the task and report back when done. "
            "NEVER use spawn for delayed/scheduled tasks — subagents cannot sleep or wait."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
            },
            "required": ["task"],
        }

    async def execute(self, task: str, label: str | None = None, **kwargs: Any) -> str:
        """Spawn a subagent to execute the given task."""
        # Structurally block delayed tasks — LLMs ignore prompt-level instructions
        if _DELAY_PATTERN.search(task):
            return (
                "ERROR: Cannot use spawn for delayed/scheduled tasks. "
                "Subagents cannot sleep or wait — commands timeout after 30-60s. "
                "Use the cron tool instead: set 'at' to the future timestamp and "
                "describe the action in 'message'. The cron system will process "
                "actionable tasks through the agent when the timer fires."
            )
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
