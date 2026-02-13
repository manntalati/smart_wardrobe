"""
Shopping suggestion engine.
Identifies gaps in the user's wardrobe and recommends items to purchase
using embedding analysis and Gemini LLM.
"""
import os
import json
from collections import Counter
import google.generativeai as genai
from dotenv import load_dotenv
from models.database import SessionLocal, ClothingItem
from services.rag import retrieve_fashion_context

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Essential wardrobe categories for a well-rounded capsule wardrobe
ESSENTIAL_CATEGORIES = {
    "casual": ["t-shirt", "jeans", "sneakers", "hoodie", "shorts"],
    "work": ["shirt", "pants", "blouse", "belt", "dress"],
    "formal": ["suit", "dress", "heels", "boots", "belt"],
    "outerwear": ["jacket", "coat"],
    "versatile": ["sweater", "cardigan", "scarf"],
}

ESSENTIAL_COLORS = ["black", "white", "navy blue", "grey", "beige", "brown"]


def analyze_wardrobe_gaps(occasion_focus: str = None) -> dict:
    """
    Analyze the user's wardrobe for gaps and generate shopping suggestions.
    """
    db = SessionLocal()
    try:
        items = db.query(ClothingItem).all()

        if not items:
            return {
                "gaps": ["Your wardrobe is empty!"],
                "suggestions": [],
                "analysis": {
                    "total_items": 0,
                    "message": "Start by uploading some clothing items to get personalized suggestions.",
                },
            }

        # Analyze what the user has
        analysis = _analyze_existing_wardrobe(items)

        # Identify gaps
        gaps = _identify_gaps(analysis, occasion_focus)

        # Generate suggestions
        if GEMINI_API_KEY:
            suggestions = _generate_shopping_suggestions(analysis, gaps, occasion_focus)
        else:
            suggestions = _fallback_suggestions(gaps)

        return {
            "gaps": gaps,
            "suggestions": suggestions,
            "analysis": analysis,
        }
    finally:
        db.close()


def _analyze_existing_wardrobe(items: list[ClothingItem]) -> dict:
    """Analyze the existing wardrobe composition."""
    categories = Counter(item.category for item in items)
    colors = Counter(item.color for item in items)
    seasons = Counter(item.season for item in items)
    fabrics = Counter(item.fabric for item in items)

    occasion_tags = []
    for item in items:
        if item.occasion_tags:
            try:
                tags = json.loads(item.occasion_tags)
                occasion_tags.extend(tags)
            except json.JSONDecodeError:
                pass
    occasions = Counter(occasion_tags)

    return {
        "total_items": len(items),
        "categories": dict(categories),
        "colors": dict(colors),
        "seasons": dict(seasons),
        "fabrics": dict(fabrics),
        "occasions": dict(occasions),
    }


def _identify_gaps(analysis: dict, occasion_focus: str = None) -> list[str]:
    """Identify wardrobe gaps based on analysis."""
    gaps = []
    existing_categories = set(analysis["categories"].keys())
    existing_colors = set(analysis["colors"].keys())

    # Check for missing essential categories
    all_essentials = set()
    if occasion_focus and occasion_focus in ESSENTIAL_CATEGORIES:
        all_essentials = set(ESSENTIAL_CATEGORIES[occasion_focus])
    else:
        for cats in ESSENTIAL_CATEGORIES.values():
            all_essentials.update(cats)

    missing_categories = all_essentials - existing_categories
    for cat in missing_categories:
        gaps.append(f"Missing clothing type: {cat}")

    # Check for missing essential/neutral colors
    missing_colors = set(ESSENTIAL_COLORS) - existing_colors
    if len(missing_colors) >= 3:
        gaps.append(f"Limited neutral colors — consider adding: {', '.join(list(missing_colors)[:3])}")

    # Check for seasonal gaps
    if "fall/winter" not in analysis["seasons"]:
        gaps.append("No fall/winter items — you may need warmer clothing")
    if "spring/summer" not in analysis["seasons"]:
        gaps.append("No spring/summer items — you may need lighter clothing")

    # Check category balance
    tops_count = sum(analysis["categories"].get(c, 0) for c in ["t-shirt", "shirt", "blouse", "sweater", "hoodie", "tank top", "cardigan"])
    bottoms_count = sum(analysis["categories"].get(c, 0) for c in ["jeans", "pants", "shorts", "skirt"])
    shoes_count = sum(analysis["categories"].get(c, 0) for c in ["sneakers", "boots", "sandals", "heels"])

    if tops_count > 0 and bottoms_count == 0:
        gaps.append("No bottoms in your wardrobe — add pants, jeans, or skirts")
    if tops_count == 0 and bottoms_count > 0:
        gaps.append("No tops in your wardrobe — add shirts, t-shirts, or blouses")
    if shoes_count == 0 and (tops_count > 0 or bottoms_count > 0):
        gaps.append("No shoes in your wardrobe — footwear completes any outfit")

    if not gaps:
        gaps.append("Your wardrobe looks well-rounded! Here are some suggestions to enhance it.")

    return gaps


def _generate_shopping_suggestions(
    analysis: dict, gaps: list[str], occasion_focus: str = None
) -> list[dict]:
    """Use Gemini to generate contextual shopping recommendations."""
    fashion_context = retrieve_fashion_context(
        f"essential wardrobe items for {occasion_focus or 'versatile'} style",
        top_k=3,
    )

    prompt = f"""You are a personal fashion advisor. Based on the user's current wardrobe analysis and identified gaps, suggest specific items to purchase.

CURRENT WARDROBE ANALYSIS:
- Total items: {analysis['total_items']}
- Categories: {json.dumps(analysis['categories'])}
- Colors: {json.dumps(analysis['colors'])}
- Seasons: {json.dumps(analysis['seasons'])}

IDENTIFIED GAPS:
{chr(10).join(f'- {g}' for g in gaps)}

{'FOCUS: ' + occasion_focus + ' wardrobe' if occasion_focus else ''}

{'FASHION GUIDANCE:' + chr(10) + chr(10).join(fashion_context) if fashion_context else ''}

Suggest 3-5 specific items to purchase. For each, explain why it would complement the existing wardrobe.

Respond in valid JSON format ONLY:
{{
  "suggestions": [
    {{
      "item": "Item description (e.g., 'Navy wool blazer')",
      "category": "category name",
      "reason": "Why this item fills a gap in the wardrobe",
      "priority": "high/medium/low",
      "estimated_price_range": "$XX - $XX"
    }}
  ]
}}"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        return result.get("suggestions", [])
    except Exception as e:
        print(f"Gemini shopping suggestion error: {e}")
        return _fallback_suggestions(gaps)


def _fallback_suggestions(gaps: list[str]) -> list[dict]:
    """Rule-based fallback shopping suggestions."""
    suggestions = []
    for gap in gaps[:5]:
        if "Missing clothing type:" in gap:
            category = gap.replace("Missing clothing type: ", "")
            suggestions.append({
                "item": f"A versatile {category} in a neutral color",
                "category": category,
                "reason": gap,
                "priority": "high",
                "estimated_price_range": "$30 - $80",
            })
        elif "neutral colors" in gap.lower():
            suggestions.append({
                "item": "Basic wardrobe staples in black, white, or navy",
                "category": "basics",
                "reason": gap,
                "priority": "medium",
                "estimated_price_range": "$20 - $50",
            })

    return suggestions
