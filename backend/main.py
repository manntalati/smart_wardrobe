"""
Smart Wardrobe — FastAPI Backend
Main application with all REST API endpoints.
"""
import os
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from models.database import init_db, get_db, ClothingItem
from services.classifier import classify_clothing, get_image_embedding
from services.embeddings import get_embedding_index
from services.recommender import get_outfit_recommendations
from services.shopping import analyze_wardrobe_gaps

load_dotenv()

app = FastAPI(
    title="Smart Wardrobe API",
    description="Intelligent wardrobe assistant with AI-powered clothing classification and outfit recommendations",
    version="1.0.0",
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


# ─── Wardrobe Endpoints ─────────────────────────────────────────────────────

@app.post("/api/items")
async def upload_item(
    image: UploadFile = File(...),
    name: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a clothing image and classify it using CLIP.
    Returns the created item with AI-detected attributes.
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save the uploaded image
    ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Read the entire file content first (important for async UploadFile)
    contents = await image.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        # Classify the image with CLIP
        classification = classify_clothing(filepath)

        # Generate CLIP embedding
        embedding = get_image_embedding(filepath)

        # Create database record
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
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        # Add to FAISS index
        idx = get_embedding_index()
        idx.add_item(item.id, embedding)

        return {
            "status": "success",
            "item": item.to_dict(),
            "classification": classification,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Clean up uploaded file on error
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@app.get("/api/items")
def list_items(db: Session = Depends(get_db)):
    """List all wardrobe items."""
    items = db.query(ClothingItem).order_by(ClothingItem.created_at.desc()).all()
    return {
        "items": [item.to_dict() for item in items],
        "total": len(items),
    }


@app.get("/api/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single wardrobe item by ID."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": item.to_dict()}


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a wardrobe item."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Remove image file
    if item.image_path:
        full_path = os.path.join(os.path.dirname(__file__), item.image_path.lstrip("/"))
        if os.path.exists(full_path):
            os.remove(full_path)

    # Remove from FAISS index
    idx = get_embedding_index()
    idx.remove_item(item_id)

    db.delete(item)
    db.commit()

    return {"status": "deleted", "id": item_id}


@app.get("/api/items/{item_id}/similar")
def find_similar(item_id: int, k: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """Find items similar to a given item using FAISS embedding search."""
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item or not item.embedding_json:
        raise HTTPException(status_code=404, detail="Item not found or has no embedding")

    embedding = json.loads(item.embedding_json)
    idx = get_embedding_index()
    results = idx.search_similar(embedding, k=k, exclude_id=item_id)

    similar_items = []
    for sim_id, score in results:
        sim_item = db.query(ClothingItem).filter(ClothingItem.id == sim_id).first()
        if sim_item:
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
):
    """Get AI-powered outfit recommendations."""
    result = get_outfit_recommendations(
        occasion=occasion,
        city=city,
        num_outfits=num_outfits,
        style_preference=style,
    )
    return result


# ─── Shopping Endpoints ────────────────────────────────────────────────────

@app.get("/api/shopping")
def shopping_suggestions(
    occasion: str = Query(None, description="Focus on specific occasion"),
):
    """Get shopping suggestions based on wardrobe gap analysis."""
    result = analyze_wardrobe_gaps(occasion_focus=occasion)
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
    }
