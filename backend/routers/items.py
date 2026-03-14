"""Wardrobe item routes."""
import os
import json
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, ClothingItem
from models.user import User
from services.classifier import classify_clothing, get_image_embedding
from services.embeddings import get_embedding_index
from services.image_optimizer import optimize_image
from services.auth import get_current_user
from config import UPLOAD_DIR, THUMBNAIL_DIR
from schemas import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/items", tags=["items"])


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("")
async def upload_item(
    image: UploadFile = File(...),
    name: str = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a clothing image, optimise it, classify with CLIP, and index."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    stem = uuid.uuid4().hex
    ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    temp_path = os.path.join(UPLOAD_DIR, f"{stem}{ext}")

    contents = await image.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    paths: dict = {}
    try:
        paths = optimize_image(temp_path, stem, UPLOAD_DIR, THUMBNAIL_DIR)
        filepath = paths["display_filepath"]

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
            image_path=paths["display_path"],
            embedding_json=json.dumps(embedding),
            confidence=classification["confidence"],
            user_id=user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        idx = get_embedding_index()
        idx.add_item(item.id, embedding, user_id=user.id)

        return ok({"item": item.to_dict(), "classification": classification})

    except Exception as e:
        logger.exception("Upload failed for user %s", user.id)
        for p in [temp_path, paths.get("display_filepath", ""), paths.get("thumbnail_filepath", "")]:
            if p and os.path.exists(p):
                os.remove(p)
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


# ── Add from URL ──────────────────────────────────────────────────────────────

class AddFromUrlRequest(BaseModel):
    image_url: str
    name: Optional[str] = None


@router.post("/from-url")
def add_item_from_url(
    request: AddFromUrlRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download an image from a URL, classify it, and add it to the wardrobe."""
    from services.search import download_image

    try:
        raw_path = download_image(request.image_url, UPLOAD_DIR)
        stem = os.path.splitext(os.path.basename(raw_path))[0]
        paths = optimize_image(raw_path, stem, UPLOAD_DIR, THUMBNAIL_DIR)
        filepath = paths["display_filepath"]

        classification = classify_clothing(filepath)
        embedding = get_image_embedding(filepath)

        item = ClothingItem(
            name=request.name or f"{classification['color'].title()} {classification['category'].title()}",
            category=classification["category"],
            color=classification["color"],
            pattern=classification["pattern"],
            season=classification["season"],
            fabric=classification["fabric"],
            occasion_tags=json.dumps(classification["occasion_tags"]),
            image_path=paths["display_path"],
            embedding_json=json.dumps(embedding),
            confidence=classification["confidence"],
            user_id=user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        idx = get_embedding_index()
        idx.add_item(item.id, embedding, user_id=user.id)

        return ok({"item": item.to_dict(), "classification": classification})

    except Exception as e:
        logger.exception("Add from URL failed: %s", request.image_url)
        raise HTTPException(status_code=500, detail=str(e))


# ── List (paginated) ──────────────────────────────────────────────────────────

@router.get("")
def list_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a paginated list of the current user's wardrobe items."""
    offset = (page - 1) * limit
    base_q = db.query(ClothingItem).filter(ClothingItem.user_id == user.id)
    total = base_q.count()
    items = base_q.order_by(ClothingItem.created_at.desc()).offset(offset).limit(limit).all()
    return ok(
        [item.to_dict() for item in items],
        meta={"total": total, "page": page, "limit": limit},
    )


# ── Similar items (before /{item_id} to avoid ambiguity) ─────────────────────

@router.get("/{item_id}/similar")
def find_similar(
    item_id: int,
    k: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find wardrobe items visually similar to a given item."""
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id, ClothingItem.user_id == user.id
    ).first()
    if not item or not item.embedding_json:
        raise HTTPException(status_code=404, detail="Item not found or has no embedding")

    embedding = json.loads(item.embedding_json)
    idx = get_embedding_index()
    results = idx.search_similar(embedding, k=k, exclude_id=item_id, user_id=user.id)

    similar = []
    for sim_id, score in results:
        sim_item = db.query(ClothingItem).filter(
            ClothingItem.id == sim_id, ClothingItem.user_id == user.id
        ).first()
        if sim_item:
            d = sim_item.to_dict()
            d["similarity_score"] = round(score, 3)
            similar.append(d)

    return ok(similar)


# ── Get single ────────────────────────────────────────────────────────────────

@router.get("/{item_id}")
def get_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id, ClothingItem.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ok(item.to_dict())


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id, ClothingItem.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.image_path:
        filename = os.path.basename(item.image_path)
        for p in [
            os.path.join(UPLOAD_DIR, filename),
            os.path.join(THUMBNAIL_DIR, filename),
        ]:
            if os.path.exists(p):
                os.remove(p)

    idx = get_embedding_index()
    idx.remove_item(item_id)

    db.delete(item)
    db.commit()

    return ok({"id": item_id})


# ── Edit ──────────────────────────────────────────────────────────────────────

class ItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    occasion_tags: Optional[list[str]] = None
    season: Optional[str] = None
    notes: Optional[str] = None


@router.patch("/{item_id}")
def update_item(
    item_id: int,
    body: ItemUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update editable fields on a wardrobe item."""
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id, ClothingItem.user_id == user.id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if body.name is not None:
        item.name = body.name
    if body.occasion_tags is not None:
        item.occasion_tags = json.dumps(body.occasion_tags)
    if body.season is not None:
        item.season = body.season
    if body.notes is not None:
        item.notes = body.notes

    db.commit()
    db.refresh(item)
    return ok(item.to_dict())
