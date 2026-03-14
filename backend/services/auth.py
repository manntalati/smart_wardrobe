"""
Authentication service for Google Sign-In and JWT management.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.database import get_db
from models.user import User

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    delta = expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + delta
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_google_token(token: str):
    # DEVELOPMENT BYPASS
    # If no client ID is set, or if using a special test token, return mock data
    if token == "test-token" or not GOOGLE_CLIENT_ID:
        print("⚠️ USING DEV AUTH BYPASS")
        return {
            "email": "testuser@example.com",
            "sub": "test-google-id-123",
            "name": "Test User",
            "picture": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
        }

    try:
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        return id_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Returns the current user if the token is valid, otherwise None."""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except Exception:
        return None
