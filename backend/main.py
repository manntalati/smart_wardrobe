"""
Smart Wardrobe — FastAPI Backend
Main application with all REST API endpoints.
"""
import os
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from pydantic import BaseModel

from models.database import init_db, get_db, ClothingItem
from models.user import User  # Import User to register with SQLAlchemy Base
from services.classifier import classify_clothing, get_image_embedding
from services.embeddings import get_embedding_index
from services.recommender import get_outfit_recommendations
from services.shopping import analyze_wardrobe_gaps
from services.auth import verify_google_token, create_access_token, get_current_user, get_optional_user
from services.search import search_images, download_image

load_dotenv()

app = FastAPI(
    title="Smart Wardrobe API",
    description="Intelligent wardrobe assistant with AI-powered clothing classification and outfit recommendations",
    version="2.0.0",
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local image storage
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount uploads directory for serving images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def startup():
    init_db()
    print("✅ Database initialized")
    print(f"📁 Upload directory: {UPLOAD_DIR}")


# ─── Auth Endpoints ─────────────────────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    token: str

@app.post("/api/auth/login")
def login(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Exchange Google ID token for JWT access token."""
    # Verify Google token
    id_info = verify_google_token(request.token)
    email = id_info['email']
    google_id = id_info['sub']
    name = id_info.get('name')
    picture = id_info.get('picture')

    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            google_id=google_id,
            full_name=name,
            avatar_url=picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create JWT
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user.to_dict()}


# ─── Search Endpoints (Search-to-Add) ───────────────────────────────────────

@app.get("/api/search")
def search_items(q: str = Query(..., min_length=2), user: User = Depends(get_current_user)):
    """Search for clothing images using DuckDuckGo."""
    images = search_images(q, max_results=20)
    return {"images": images}

class AddFromUrlRequest(BaseModel):
    image_url: str
    name: str = None

@app.post("/api/items/from-url")
def add_item_from_url(
    request: AddFromUrlRequest,
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Download image from URL, classify, and add to wardrobe."""
    try:
        # Download image
        filepath = download_image(request.image_url, UPLOAD_DIR)
        filename = os.path.basename(filepath)

        # Classify
        classification = classify_clothing(filepath)
        embedding = get_image_embedding(filepath)

        # Create Record
        item = ClothingItem(
            name=request.name or f"{classification['color'].title()} {classification['category'].title()}",
            category=classification["category"],
            color=classification["color"],
            pattern=classification["pattern"],
            season=classification["season"],
            fabric=classification["fabric"],
            occasion_tags=json.dumps(classification["occasion_tags"]),
            image_path=f"/uploads/{filename}",
            embedding_json=json.dumps(embedding),
            confidence=classification["confidence"],
            user_id=user.id # Link to user
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        # Add to FAISS
        idx = get_embedding_index()
        idx.add_item(item.id, embedding, user_id=user.id)

        return {
            "status": "success",
            "item": item.to_dict(),
            "classification": classification,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Wardrobe Endpoints ─────────────────────────────────────────────────────

@app.post("/api/items")
async def upload_item(
    image: UploadFile = File(...),
    name: str = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a clothing image and classify it using CLIP."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    contents = await image.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        classification = classify_clothing(filepath)
        embedding = get_image_embedding(filepath)

        item = ClothingItem(
            name=name or f"{classification['color'].title()} {classification['category'].title()}",
            category=classification["category"],
            color=classification["color"],
            pattern=classification["pattern"],
            season=classification["season"],
            fabric=classification["fabric"],
            occasion_tags=json.dumps(classification["occasion_tags"]),
            image_path=f"/uploads/{filename}",
            embedding_json=json.dumps(embedding),
            confidence=classification["confidence"],
            user_id=user.id # Link to user
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        idx = get_embedding_index()
        idx.add_item(item.id, embedding, user_id=user.id)

        return {
            "status": "success",
            "item": item.to_dict(),
            "classification": classification,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.get("/api/items")
def list_items(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all wardrobe items for the current user."""
    # Filter by user_id
    items = db.query(ClothingItem).filter(ClothingItem.user_id == user.id).order_by(ClothingItem.created_at.desc()).all()
    return {
        "items": [item.to_dict() for item in items],
        "total": len(items),
    }


@app.get("/api/items/{item_id}")
def get_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single wardrobe item by ID (must belong to user)."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id, ClothingItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": item.to_dict()}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a wardrobe item."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id, ClothingItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.image_path:
        full_path = os.path.join(os.path.dirname(__file__), item.image_path.lstrip("/"))
        if os.path.exists(full_path):
            os.remove(full_path)

    idx = get_embedding_index()
    idx.remove_item(item_id)

    db.delete(item)
    db.commit()

    return {"status": "deleted", "id": item_id}


@app.get("/api/items/{item_id}/similar")
def find_similar(
    item_id: int, 
    k: int = Query(5, ge=1, le=20), 
    user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Find items similar to a given item using FAISS embedding search."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id, ClothingItem.user_id == user.id).first()
    if not item or not item.embedding_json:
        raise HTTPException(status_code=404, detail="Item not found or has no embedding")

    embedding = json.loads(item.embedding_json)
    idx = get_embedding_index()
    # Pass user_id to filter results
    results = idx.search_similar(embedding, k=k, exclude_id=item_id, user_id=user.id)

    similar_items = []
    for sim_id, score in results:
        # DB lookup to double check ownership and get details
        sim_item = db.query(ClothingItem).filter(ClothingItem.id == sim_id).first() 
        # Note: We don't strictly enforce user_id here if FAISS did its job, but good for safety
        if sim_item and sim_item.user_id == user.id:
            d = sim_item.to_dict()
            d["similarity_score"] = round(score, 3)
            similar_items.append(d)

    return {"similar_items": similar_items}


# ─── Recommendation Endpoints ──────────────────────────────────────────────

@app.get("/api/recommendations")
def recommend_outfits(
    occasion: str = Query("casual", description="Occasion type"),
    city: str = Query(None, description="City for weather-based recommendations"),
    num_outfits: int = Query(3, ge=1, le=10),
    style: str = Query(None, description="Style preference"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)  # Need DB to get items
):
    """Get AI-powered outfit recommendations."""
    # We need to pass user to get_outfit_recommendations
    # I need to update the service function to accept user_id or list of items
    result = get_outfit_recommendations(
        occasion=occasion,
        city=city,
        num_outfits=num_outfits,
        style_preference=style,
        user_id=user.id, # New parameter
        db=db # Pass DB session
    )
    return result


# ─── Shopping Endpoints ────────────────────────────────────────────────────

@app.get("/api/shopping")
def shopping_suggestions(
    occasion: str = Query(None, description="Focus on specific occasion"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get shopping suggestions based on wardrobe gap analysis."""
    result = analyze_wardrobe_gaps(
        occasion_focus=occasion,
        user_id=user.id,
        db=db
    )
    return result


# ─── Health Check ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "Smart Wardrobe API",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "weather_configured": bool(os.getenv("OPENWEATHER_API_KEY")),
        "google_auth_configured": bool(os.getenv("GOOGLE_CLIENT_ID")),
    }
