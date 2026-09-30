"""Run the standalone ISS timekeeping API."""

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "iss_module.api.api:app",
        host=os.getenv("ISS_HOST", "127.0.0.1"),
        port=int(os.getenv("ISS_PORT", "8000")),
        reload=os.getenv("ISS_RELOAD", "false").lower() == "true",
        log_level=os.getenv("ISS_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
