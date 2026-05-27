from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_status():
    """Check if the server is running."""
    return {
        "status": "ok",
        "message": "Gema proxy server is running",
        "version": "0.1.0",
    }
