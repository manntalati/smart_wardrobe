"""
CLIP-based clothing classifier using zero-shot classification.
Classifies uploaded clothing images across multiple dimensions:
category, color, pattern, season, and fabric.
"""
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from functools import lru_cache

# Classification labels for each dimension
CATEGORIES = [
    "t-shirt", "shirt", "blouse", "sweater", "hoodie",
    "jacket", "coat", "jeans", "pants", "shorts",
    "skirt", "dress", "suit", "sneakers", "boots",
    "sandals", "heels", "hat", "scarf", "bag",
    "belt", "watch", "jewelry", "tank top", "cardigan",
]

COLORS = [
    "black", "white", "navy blue", "grey", "beige",
    "brown", "red", "blue", "green", "pink",
    "yellow", "purple", "orange", "multicolor", "cream",
]

PATTERNS = [
    "solid color", "striped", "plaid", "floral",
    "polka dot", "graphic print", "abstract pattern",
    "animal print", "camouflage", "checkered",
]

SEASONS = [
    "spring/summer lightweight clothing",
    "fall/winter warm clothing",
    "all-season versatile clothing",
]

FABRICS = [
    "cotton", "denim", "leather", "silk", "wool",
    "polyester", "linen", "knit", "suede", "velvet",
]

OCCASIONS = [
    "casual everyday wear",
    "business/work professional",
    "formal/dressy occasion",
    "athletic/sportswear",
    "party/night out",
    "outdoor/adventure",
]

MODEL_NAME = "openai/clip-vit-base-patch32"

_model = None
_processor = None


def _get_model():
    """Lazy-load the CLIP model and processor."""
    global _model, _processor
    if _model is None:
        print("Loading CLIP model... (this may take a moment on first run)")
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()
        print("CLIP model loaded successfully.")
    return _model, _processor


def _classify_dimension(image: Image.Image, labels: list[str], prefix: str = "") -> tuple[str, float]:
    """
    Run zero-shot classification for a single dimension.
    Returns (best_label, confidence_score).
    """
    model, processor = _get_model()

    # Add descriptive prefix to labels for better CLIP accuracy
    text_labels = [f"a photo of {prefix}{label}" for label in labels]

    inputs = processor(
        text=text_labels,
        images=image,
        return_tensors="pt",
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits_per_image[0]
        probs = logits.softmax(dim=0)

    best_idx = probs.argmax().item()
    return labels[best_idx], probs[best_idx].item()


def classify_clothing(image_path: str) -> dict:
    """
    Classify a clothing image across all dimensions.
    Returns a dict with category, color, pattern, season, fabric, occasion, and confidence.
    """
    image = Image.open(image_path).convert("RGB")

    category, cat_conf = _classify_dimension(image, CATEGORIES, prefix="a ")
    color, _ = _classify_dimension(image, COLORS, prefix="")
    pattern, _ = _classify_dimension(image, PATTERNS, prefix="a clothing item with ")
    season, _ = _classify_dimension(image, SEASONS, prefix="")
    fabric, _ = _classify_dimension(image, FABRICS, prefix="a clothing item made of ")
    occasion, _ = _classify_dimension(image, OCCASIONS, prefix="")

    # Clean up season label
    season_clean = season.replace(" lightweight clothing", "").replace(" warm clothing", "").replace(" versatile clothing", "")
    # Clean up occasion label
    occasion_clean = occasion.split("/")[0].strip() if "/" in occasion else occasion.split(" ")[0]

    return {
        "category": category,
        "color": color,
        "pattern": pattern.replace(" color", "").replace(" pattern", "").replace(" print", ""),
        "season": season_clean,
        "fabric": fabric,
        "occasion_tags": [occasion_clean],
        "confidence": round(cat_conf, 3),
    }


def get_image_embedding(image_path: str) -> list[float]:
    """
    Generate a CLIP image embedding for a clothing item.
    Returns a list of floats (512-d vector).
    """
    model, processor = _get_model()
    image = Image.open(image_path).convert("RGB")

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        embedding = outputs[0].cpu().numpy().tolist()

    return embedding
