"""Image search routes (DuckDuckGo search-to-add)."""
from fastapi import APIRouter, Depends, Query

from models.user import User
from services.search import search_images
from services.auth import get_current_user
from schemas import ok

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user),
):
    """Search for clothing images via DuckDuckGo."""
    images = search_images(q, max_results=20)
    return ok({"images": images})
