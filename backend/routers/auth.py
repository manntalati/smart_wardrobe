"""Auth routes — Google OAuth token exchange."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db
from models.user import User
from services.auth import verify_google_token, create_access_token
from schemas import ok

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    token: str


@router.post("/login")
def login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Exchange a Google ID token for a JWT access token."""
    id_info = verify_google_token(request.token)

    user = db.query(User).filter(User.email == id_info["email"]).first()
    if not user:
        user = User(
            email=id_info["email"],
            google_id=id_info["sub"],
            full_name=id_info.get("name"),
            avatar_url=id_info.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    return ok({"access_token": access_token, "token_type": "bearer", "user": user.to_dict()})
