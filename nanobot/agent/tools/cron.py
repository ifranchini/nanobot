"""Cron tool for scheduling reminders and tasks."""

from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


class CronTool(Tool):
    """Tool to schedule reminders and recurring tasks."""
    
    def __init__(self, cron_service: CronService):
        self._cron = cron_service
        self._channel = ""
        self._chat_id = ""
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the current session context for delivery."""
        self._channel = channel
        self._chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "cron"
    
    @property
    def description(self) -> str:
        return (
            "Schedule reminders, delayed tasks, and recurring tasks. Actions: add, list, remove. "
            "You MUST call this tool whenever the user asks for a reminder — never "
            "claim a reminder was set without calling this tool first. "
            "For delayed tasks (e.g. 'send email in 10 min'), set task=true so the "
            "message is processed by you (the agent) when the timer fires, not just "
            "delivered as text. "
            "IMPORTANT: Always pass the user's timezone via the tz parameter "
            "(e.g. 'America/Los_Angeles') or include timezone offset in the at "
            "parameter (e.g. '2026-02-12T10:30:00-08:00'). Never use naive datetimes."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove"],
                    "description": "Action to perform"
                },
                "message": {
                    "type": "string",
                    "description": "Reminder message (for add)"
                },
                "every_seconds": {
                    "type": "integer",
                    "description": "Interval in seconds (for recurring tasks)"
                },
                "cron_expr": {
                    "type": "string",
                    "description": "Cron expression like '0 9 * * *' (for scheduled tasks)"
                },
                "tz": {
                    "type": "string",
                    "description": (
                        "IANA timezone (e.g. 'America/Los_Angeles'). "
                        "Used with cron_expr or at. ALWAYS pass the user's timezone."
                    ),
                },
                "at": {
                    "type": "string",
                    "description": (
                        "ISO datetime for one-time execution. MUST include "
                        "timezone offset (e.g. '2026-02-12T10:30:00-08:00') "
                        "or pair with tz parameter."
                    ),
                },
                "job_id": {
                    "type": "string",
                    "description": "Job ID (for remove)"
                },
                "task": {
                    "type": "boolean",
                    "description": (
                        "If true, the message is processed by the agent when the "
                        "timer fires (for delayed tasks like 'send email in 10 min'). "
                        "If false (default), the message is delivered directly as a "
                        "reminder notification."
                    ),
                }
            },
            "required": ["action"]
        }
    
    async def execute(
        self,
        action: str,
        message: str = "",
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str | None = None,
        at: str | None = None,
        job_id: str | None = None,
        task: bool = False,
        **kwargs: Any
    ) -> str:
        if action == "add":
            return self._add_job(message, every_seconds, cron_expr, tz, at, task)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(job_id)
        return f"Unknown action: {action}"
    
    def _add_job(
        self,
        message: str,
        every_seconds: int | None,
        cron_expr: str | None,
        tz: str | None,
        at: str | None,
        task: bool = False,
    ) -> str:
        if not message:
            return "Error: message is required for add"
        if not self._channel or not self._chat_id:
            return "Error: no session context (channel/chat_id)"
        if tz:
            from zoneinfo import ZoneInfo
            try:
                ZoneInfo(tz)
            except (KeyError, Exception):
                return f"Error: unknown timezone '{tz}'"

        # Build schedule
        delete_after = False
        if every_seconds:
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        elif cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr, tz=tz)
        elif at:
            from datetime import datetime
            dt = datetime.fromisoformat(at)
            # If naive datetime and tz provided, localize it
            if dt.tzinfo is None and tz:
                from zoneinfo import ZoneInfo
                dt = dt.replace(tzinfo=ZoneInfo(tz))
            at_ms = int(dt.timestamp() * 1000)
            schedule = CronSchedule(kind="at", at_ms=at_ms)
            delete_after = True
        else:
            return "Error: either every_seconds, cron_expr, or at is required"
        
        job = self._cron.add_job(
            name=message[:30],
            schedule=schedule,
            message=message,
            deliver=not task,
            channel=self._channel,
            to=self._chat_id,
            delete_after_run=delete_after,
        )
        return f"Created job '{job.name}' (id: {job.id})"
    
    def _list_jobs(self) -> str:
        from datetime import datetime, timezone
        jobs = self._cron.list_jobs()
        if not jobs:
            return "No scheduled jobs."
        lines = []
        for j in jobs:
            next_run = ""
            if j.state.next_run_at_ms:
                dt = datetime.fromtimestamp(j.state.next_run_at_ms / 1000, tz=timezone.utc)
                next_run = f", next: {dt.strftime('%Y-%m-%d %H:%M UTC')}"
            sched = j.schedule.kind
            if j.schedule.expr:
                sched = f"cron '{j.schedule.expr}'"
                if j.schedule.tz:
                    sched += f" ({j.schedule.tz})"
            lines.append(f"- {j.name} (id: {j.id}, {sched}{next_run})")
        return "Scheduled jobs:\n" + "\n".join(lines)
    
    def _remove_job(self, job_id: str | None) -> str:
        if not job_id:
            return "Error: job_id is required for remove"
        if self._cron.remove_job(job_id):
            return f"Removed job {job_id}"
        return f"Job {job_id} not found"
