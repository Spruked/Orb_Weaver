"""Core timekeeping service state."""

from datetime import datetime, timezone

from .utils import current_timecodes


class ISS:
    """Provide service status alongside the current time representations."""

    def __init__(self, system_name: str = "ISS"):
        self.system_name = system_name
        self.status = "healthy"
        self.startup_time = datetime.now(timezone.utc)

    def heartbeat(self) -> bool:
        return self.status == "healthy"

    def get_status(self) -> dict:
        timecodes = current_timecodes()
        uptime = datetime.now(timezone.utc) - self.startup_time
        return {
            "status": self.status,
            "system_name": self.system_name,
            "startup_time": self.startup_time.isoformat(),
            "uptime": str(uptime).split(".")[0],
            "time": timecodes,
        }

    async def shutdown(self) -> None:
        self.status = "stopped"
