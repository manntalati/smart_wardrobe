"""Shopping / wardrobe gap analysis routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from models.database import get_db
from models.user import User
from services.shopping import analyze_wardrobe_gaps
from services.auth import get_current_user
from schemas import ok

router = APIRouter(prefix="/api/v1/shopping", tags=["shopping"])


@router.get("")
def shopping_suggestions(
    occasion: str = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return shopping suggestions based on wardrobe gap analysis."""
    result = analyze_wardrobe_gaps(
        occasion_focus=occasion,
        user_id=user.id,
        db=db,
    )
    return ok(result)
