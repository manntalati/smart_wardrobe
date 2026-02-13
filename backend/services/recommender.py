"""
Outfit recommendation engine.
Combines wardrobe data, weather context, occasion, FAISS similarity search,
RAG fashion knowledge, and Gemini LLM to generate outfit suggestions.
"""
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from models.database import SessionLocal, ClothingItem
from services.weather import get_weather
from services.rag import retrieve_fashion_context
from services.embeddings import get_embedding_index

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def get_outfit_recommendations(
    occasion: str = "casual",
    city: str = None,
    num_outfits: int = 3,
    style_preference: str = None,
    user_id: int = None,
    db: SessionLocal = None,
) -> dict:
    """
    Generate outfit recommendations using the full pipeline:
    1. Fetch weather (if city provided)
    2. Load wardrobe items from database
    3. Retrieve fashion context via RAG
    4. Generate outfit suggestions using Gemini
    """
    # 1. Fetch weather
    weather_data = None
    if city:
        weather_data = get_weather(city)

    # 2. Load wardrobe
    # Use passed DB session or create new one (fallback for standalone testing)
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query = db.query(ClothingItem)
        if user_id:
            query = query.filter(ClothingItem.user_id == user_id)
        
        items = query.all()
        
        if not items:
            return {
                "outfits": [],
                "message": "Your wardrobe is empty! Upload some clothing items first.",
                "weather": weather_data,
            }

        wardrobe_summary = _build_wardrobe_summary(items)
    finally:
        if close_db:
            db.close()

    # 3. Retrieve fashion context
    rag_query = f"outfit for {occasion}"
    if weather_data:
        rag_query += f" in {weather_data['description']} weather, {weather_data['temperature_f']}°F"
    if style_preference:
        rag_query += f", {style_preference} style"

    fashion_context = retrieve_fashion_context(rag_query, top_k=3)

    # 4. Generate with Gemini
    if not GEMINI_API_KEY:
        return _fallback_recommendations(items, occasion, weather_data)

    outfits = _generate_with_gemini(
        wardrobe_summary, weather_data, occasion, style_preference,
        fashion_context, num_outfits
    )

    return {
        "outfits": outfits,
        "weather": weather_data,
        "occasion": occasion,
    }


def _build_wardrobe_summary(items: list[ClothingItem]) -> str:
    """Build a text summary of the user's wardrobe for the LLM prompt."""
    lines = []
    for item in items:
        tags = json.loads(item.occasion_tags) if item.occasion_tags else []
        line = f"- ID:{item.id} | {item.color} {item.pattern} {item.category} | {item.fabric} | Season: {item.season} | Occasions: {', '.join(tags)}"
        if item.name:
            line = f"- ID:{item.id} \"{item.name}\" | {item.color} {item.pattern} {item.category} | {item.fabric} | Season: {item.season} | Occasions: {', '.join(tags)}"
        lines.append(line)
    return "\n".join(lines)


def _generate_with_gemini(
    wardrobe_summary: str,
    weather_data: dict | None,
    occasion: str,
    style_preference: str | None,
    fashion_context: list[str],
    num_outfits: int,
) -> list[dict]:
    """Use Gemini to generate outfit recommendations."""
    weather_section = ""
    if weather_data:
        weather_section = f"""
Current Weather in {weather_data['city']}:
- Temperature: {weather_data['temperature_f']}°F (feels like {weather_data['feels_like_f']}°F)
- Conditions: {weather_data['description']}
- Humidity: {weather_data['humidity']}%
- Style hints: {'; '.join(weather_data['style_hints'])}
"""

    fashion_section = ""
    if fashion_context:
        fashion_section = "Fashion guidance:\n" + "\n---\n".join(fashion_context)

    style_section = f"\nUser's style preference: {style_preference}" if style_preference else ""

    prompt = f"""You are an expert fashion stylist. Based on the user's wardrobe, weather conditions, and occasion, suggest {num_outfits} complete outfit combinations.

WARDROBE ITEMS:
{wardrobe_summary}

OCCASION: {occasion}
{weather_section}
{fashion_section}
{style_section}

IMPORTANT RULES:
1. Only use items from the wardrobe list above (reference by their ID).
2. Each outfit should be a complete look (top, bottom, shoes at minimum).
3. Consider weather appropriateness, color coordination, and occasion suitability.
4. Provide a brief explanation for why each outfit works.

Respond in valid JSON format ONLY. Use this exact structure:
{{
  "outfits": [
    {{
      "name": "Outfit Name",
      "items": [1, 3, 7],
      "description": "A brief description of the outfit and why it works for this occasion.",
      "style_notes": "Specific styling tip for this combination."
    }}
  ]
}}"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Clean markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        return result.get("outfits", [])
    except Exception as e:
        print(f"Gemini API error: {e}")
        return []


def _fallback_recommendations(
    items: list[ClothingItem], occasion: str, weather_data: dict | None
) -> dict:
    """Simple rule-based fallback when Gemini API is not available."""
    # Group items by category
    tops = [i for i in items if i.category in ("t-shirt", "shirt", "blouse", "sweater", "hoodie", "tank top", "cardigan")]
    bottoms = [i for i in items if i.category in ("jeans", "pants", "shorts", "skirt")]
    shoes = [i for i in items if i.category in ("sneakers", "boots", "sandals", "heels")]
    outerwear = [i for i in items if i.category in ("jacket", "coat")]
    dresses = [i for i in items if i.category == "dress"]

    outfits = []

    # Generate simple combinations
    if dresses:
        for dress in dresses[:2]:
            outfit = {
                "name": f"{dress.color.title()} {dress.category.title()} Look",
                "items": [dress.id],
                "description": f"A {dress.color} {dress.pattern} {dress.category} — simple and elegant for {occasion}.",
                "style_notes": "Add accessories to elevate the look.",
            }
            if shoes:
                outfit["items"].append(shoes[0].id)
            outfits.append(outfit)

    if tops and bottoms:
        for i, top in enumerate(tops[:3]):
            if i < len(bottoms):
                bottom = bottoms[i % len(bottoms)]
                outfit = {
                    "name": f"{top.color.title()} {top.category.title()} + {bottom.color.title()} {bottom.category.title()}",
                    "items": [top.id, bottom.id],
                    "description": f"Pair the {top.color} {top.category} with {bottom.color} {bottom.category} for a {occasion} look.",
                    "style_notes": "Classic combination that works well together.",
                }
                if shoes:
                    outfit["items"].append(shoes[i % len(shoes)].id)
                if weather_data and weather_data.get("temperature_f", 70) < 55 and outerwear:
                    outfit["items"].append(outerwear[0].id)
                    outfit["style_notes"] += f" Layer with the {outerwear[0].color} {outerwear[0].category} for warmth."
                outfits.append(outfit)

    return {
        "outfits": outfits[:3],
        "weather": weather_data,
        "occasion": occasion,
        "message": "These are basic recommendations. Add your Gemini API key for AI-powered suggestions!",
    }
