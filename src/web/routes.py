"""API routes for the web dashboard."""
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/status")
async def get_status():
    """Get current harness status."""
    return {
        "status": "running",
        "version": "0.1.0",
        "uptime": "N/A",
    }


@router.get("/history")
async def get_history():
    """Get recent session history."""
    return []


@router.get("/audit")
async def get_audit():
    """Get recent audit log entries."""
    return []