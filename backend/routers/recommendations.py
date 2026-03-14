"""Outfit recommendation routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from models.database import get_db
from models.user import User
from services.recommender import get_outfit_recommendations
from services.auth import get_current_user
from schemas import ok

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("")
def recommend_outfits(
    occasion: str = Query("casual"),
    city: str = Query(None),
    num_outfits: int = Query(3, ge=1, le=10),
    style: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return AI-powered outfit suggestions for the current user."""
    result = get_outfit_recommendations(
        occasion=occasion,
        city=city,
        num_outfits=num_outfits,
        style_preference=style,
        user_id=user.id,
        db=db,
    )
    return ok(result)
