"""Ollama adapter."""

import asyncio
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List

import aiohttp

from starfish.common.logger import get_logger

logger = get_logger(__name__)

# Default Ollama connection settings
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"


class OllamaError(Exception):
    """Base exception for Ollama-related errors."""

    pass


class OllamaNotInstalledError(OllamaError):
    """Error raised when Ollama is not installed."""

    pass


class OllamaConnectionError(OllamaError):
    """Error raised when connection to Ollama server fails."""

    pass


async def is_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/version", timeout=aiohttp.ClientTimeout(total=2)) as response:
                return response.status == 200
    except Exception:
        return False


async def start_ollama_server() -> bool:
    """Start the Ollama server if it's not already running."""
    # Check if already running
    if await is_ollama_running():
        logger.info("Ollama server is already running")
        return True

    # Find the ollama executable
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        logger.error("Ollama is not installed")
        raise OllamaNotInstalledError("Ollama is not installed. Please install from https://ollama.com/download")

    logger.info("Starting Ollama server...")
    try:
        # Start Ollama as a detached process
        if os.name == "nt":  # Windows
            subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:  # Unix/Linux/Mac
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setpgrp,  # Run in a new process group
            )

        # Wait for the server to start
        for _ in range(10):
            if await is_ollama_running():
                logger.info("Ollama server started successfully")
                return True
            await asyncio.sleep(0.5)

        logger.error("Timed out waiting for Ollama server to start")
        return False

    except Exception as e:
        logger.error(f"Failed to start Ollama server: {e}")
        return False


async def list_models() -> List[Dict[str, Any]]:
    """List available models in Ollama using the API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as response:
                if response.status != 200:
                    logger.error(f"Error listing models: {response.status}")
                    return []

                data = await response.json()
                return data.get("models", [])
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []


async def is_model_available(model_name: str) -> bool:
    """Check if model is available using the CLI command."""
    try:
        # Use CLI for more reliable checking
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            logger.error("Ollama binary not found")
            return False

        process = await asyncio.create_subprocess_exec(ollama_bin, "list", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        stdout, _ = await process.communicate()
        output = stdout.decode().strip()

        # Log what models are available
        logger.debug(f"Available models: {output}")

        # Look for the model name in the output
        model_lines = output.split("\n")
        for line in model_lines:
            # Check if the line contains the model name
            if line.strip() and model_name in line.split()[0]:
                logger.info(f"Found model {model_name}")
                return True

        logger.info(f"Model {model_name} not found")
        return False

    except Exception as e:
        logger.error(f"Error checking if model is available: {e}")
        return False


async def pull_model(model_name: str) -> bool:
    """Pull a model using the Ollama CLI.
    This is more reliable than the API for large downloads.
    """
    # Use the Ollama CLI directly for more reliable downloads
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        logger.error("Ollama binary not found")
        return False

    try:
        # Set logging interval
        LOG_INTERVAL = 10  # Only log every 10 seconds
        logger.info(f"Pulling model {model_name}... (progress updates every {LOG_INTERVAL} seconds)")

        # Create the subprocess
        process = await asyncio.create_subprocess_exec(ollama_bin, "pull", model_name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Track last progress output time to throttle logging
        last_log_time = 0

        # Define functions to read from both stdout and stderr
        async def read_stream(stream, stream_name):
            nonlocal last_log_time
            buffered_content = []

            while True:
                line = await stream.readline()
                if not line:
                    break

                line_text = line.decode().strip()
                if not line_text:
                    continue

                # Fix truncated "ulling manifest" text if present
                if "ulling manifest" in line_text and not line_text.startswith("Pulling"):
                    line_text = "P" + line_text

                current_time = time.time()
                # Always log important messages like errors
                if "error" in line_text.lower() or "fail" in line_text.lower():
                    logger.info(f"Ollama pull ({stream_name}): {line_text}")
                    continue

                # Buffer regular progress messages
                buffered_content.append(line_text)

                # Log throttled progress updates
                if current_time - last_log_time >= LOG_INTERVAL:
                    if buffered_content:
                        logger.info(f"Ollama pull progress: {buffered_content[-1]}")
                        buffered_content = []
                    last_log_time = current_time

        # Read from both stdout and stderr concurrently
        await asyncio.gather(read_stream(process.stdout, "stdout"), read_stream(process.stderr, "stderr"))

        # Wait for process to complete
        exit_code = await process.wait()

        if exit_code == 0:
            logger.info(f"Successfully pulled model {model_name}")

            # Give a moment for Ollama to finalize the model
            await asyncio.sleep(1)

            # Verify model is available
            if await is_model_available(model_name):
                logger.info(f"Verified model {model_name} is now available")
                return True
            else:
                logger.error(f"Model pull completed but {model_name} not found in list")
                return False
        else:
            logger.error(f"Failed to pull model {model_name} with exit code {exit_code}")
            return False

    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {e}")
        return False


async def ensure_model_ready(model_name: str) -> bool:
    """Ensure Ollama server is running and the model is available."""
    # Step 1: Make sure Ollama server is running
    if not await start_ollama_server():
        logger.error("Failed to start Ollama server")
        return False

    # Step 2: Check if model is already available
    if await is_model_available(model_name):
        logger.info(f"Model {model_name} is already available")
        return True

    # Step 3: Pull the model if not available
    logger.info(f"Model {model_name} not found, downloading...")
    if await pull_model(model_name):
        logger.info(f"Model {model_name} successfully pulled and ready")
        return True
    else:
        logger.error(f"Failed to pull model {model_name}")
        return False


async def stop_ollama_server() -> bool:
    """Stop the Ollama server."""
    try:
        # Find the ollama executable (just to check if it's installed)
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            logger.error("Ollama is not installed")
            return False

        logger.info("Stopping Ollama server...")

        # Different process termination based on platform
        if os.name == "nt":  # Windows
            # Windows uses taskkill to terminate processes
            process = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/IM", "ollama.exe", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        else:  # Unix/Linux/Mac
            # Use pkill to terminate all Ollama processes
            process = await asyncio.create_subprocess_exec("pkill", "-f", "ollama", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        _, stderr = await process.communicate()

        # Check if the Ollama server is still running
        if await is_ollama_running():
            logger.error(f"Failed to stop Ollama server: {stderr.decode() if stderr else 'unknown error'}")
            logger.info("Attempting stronger termination...")

            # Try one more time with stronger termination if it's still running
            if os.name == "nt":  # Windows
                process = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/F",
                    "/IM",
                    "ollama.exe",
                    "/T",  # /T terminates child processes as well
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:  # Unix/Linux/Mac
                process = await asyncio.create_subprocess_exec(
                    "pkill",
                    "-9",
                    "-f",
                    "ollama",  # SIGKILL for force termination
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            _, stderr = await process.communicate()

            if await is_ollama_running():
                logger.error("Failed to forcefully stop Ollama server")
                return False

        # Wait a moment to ensure processes are actually terminated
        await asyncio.sleep(1)

        # Verify the server is no longer running
        if not await is_ollama_running():
            logger.info("Ollama server stopped successfully")
            return True
        else:
            logger.error("Failed to stop Ollama server: still running after termination attempts")
            return False

    except Exception as e:
        logger.error(f"Error stopping Ollama server: {str(e)}")
        cmd = "taskkill /F /IM ollama.exe" if os.name == "nt" else "pkill -f ollama"
        logger.error(f"Command attempted: {cmd}")
        return False


async def delete_model(model_name: str) -> bool:
    """Delete a model from Ollama.

    Args:
        model_name: The name of the model to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Find the ollama executable
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            logger.error("Ollama is not installed")
            return False

        logger.info(f"Deleting model {model_name} from Ollama...")
        process = await asyncio.create_subprocess_exec(ollama_bin, "rm", model_name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"Failed to delete model {model_name}: {stderr.decode()}")
            return False

        logger.info(f"Model {model_name} deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting model {model_name}: {e}")
        return False
