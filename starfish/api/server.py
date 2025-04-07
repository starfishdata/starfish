"""Server startup and configuration module for the Starfish API."""

import os

import uvicorn

from starfish.common.logger import get_logger

logger = get_logger(__name__)


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True, log_level: str = "info", workers: int = 1) -> None:
    """Run the Starfish API server programmatically.

    Args:
        host: Host to bind the server to
        port: Port to run the server on
        reload: Whether to enable auto-reload
        log_level: Logging level for uvicorn
        workers: Number of worker processes for uvicorn
    """
    logger.info(f"Starting Starfish API server on {host}:{port} with {workers} worker(s)...")
    os.environ["PORT"] = str(port)

    config = uvicorn.Config("starfish.api.main:app", host=host, port=port, reload=reload, log_level=log_level, workers=workers)
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    run_server()
