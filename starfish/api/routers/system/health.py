from fastapi import APIRouter, Request
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import psutil

# Use the project's custom logger instead of uvicorn's
from starfish.common.logger import get_logger
logger = get_logger(__name__)

router = APIRouter()

# Simple status tracking
last_check_time = None
start_time = time.time()
is_running = False
heartbeat_thread = None
thread_lock = threading.Lock()  # For thread-safe operations

class HealthResponse(BaseModel):
    status: str
    uptime: float
    last_check: Optional[str] = None
    cpu_usage: float
    memory_usage: Dict[str, Any]

def heartbeat_worker():
    """Heartbeat worker that uses the custom logger with timestamps"""
    global last_check_time, is_running
    
    # Thread-safe setting of running state
    with thread_lock:
        is_running = True
    
    # Get initial CPU percent without blocking (first call returns 0.0, next call returns actual value)
    psutil.cpu_percent(interval=None)
    
    try:
        # Run until told to stop
        while is_running:
            try:
                # Calculate uptime
                uptime = time.time() - start_time
                hours, remainder = divmod(int(uptime), 3600)
                minutes, seconds = divmod(remainder, 60)
                
                # Get basic system info - non-blocking calls
                cpu = psutil.cpu_percent(interval=None)  # Non-blocking
                mem = psutil.virtual_memory().percent
                
                # Update check time - thread-safe with lock
                current_time = datetime.now()
                with thread_lock:
                    last_check_time = current_time
                
                # Create heartbeat message
                heartbeat = f"❤️  HEARTBEAT [Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}] CPU: {cpu:.1f}% MEM: {mem:.1f}%"
                
                # Log through the custom logger
                logger.info(heartbeat)
                
                # Sleep for one minute - breaking into smaller sleeps allows more responsive shutdown
                # Check is_running every 5 seconds to allow quicker shutdown
                for _ in range(12):  # 12 x 5 seconds = 60 seconds
                    if not is_running:
                        break
                    time.sleep(5)
            except Exception as e:
                # Log and continue on errors within the heartbeat loop
                logger.error(f"Error in heartbeat cycle: {str(e)}")
                time.sleep(5)  # Short sleep on error before retry
                
    except Exception as e:
        logger.error(f"Heartbeat worker error: {str(e)}")
    finally:
        with thread_lock:
            is_running = False
        logger.info("Heartbeat monitoring stopped")

def start_heartbeat():
    """Start the heartbeat thread if not already running"""
    global heartbeat_thread, is_running
    
    with thread_lock:
        if is_running and heartbeat_thread and heartbeat_thread.is_alive():
            logger.info("Heartbeat monitoring already running")
            return
    
        # Create and start the thread
        heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True, 
                                           name="heartbeat-monitor")
        heartbeat_thread.start()
        
        logger.info("Health monitoring started")

def stop_heartbeat():
    """Gracefully stop the heartbeat thread"""
    global is_running, heartbeat_thread
    
    with thread_lock:
        is_running = False
    
    if heartbeat_thread and heartbeat_thread.is_alive():
        logger.info("Stopping heartbeat monitoring...")
        # No need to join - we just set the flag and let it exit naturally
        # since it checks is_running frequently

@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint"""
    # Always return healthy
    cpu = psutil.cpu_percent(interval=None)  # Non-blocking
    mem = psutil.virtual_memory()
    uptime = time.time() - start_time
    
    # If health check not running, restart it (self-healing)
    with thread_lock:
        thread_is_alive = heartbeat_thread and heartbeat_thread.is_alive()
        if not is_running or not thread_is_alive:
            logger.warning("Heartbeat monitor not running, restarting...")
            start_heartbeat()
    
    # Thread-safe access to last_check_time
    with thread_lock:
        last_check_copy = last_check_time
    
    return HealthResponse(
        status="healthy",
        uptime=uptime,
        last_check=last_check_copy.isoformat() if last_check_copy else None,
        cpu_usage=cpu,
        memory_usage={
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent
        }
    )