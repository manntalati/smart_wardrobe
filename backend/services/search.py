"""
Image search service using DuckDuckGo.
"""
from duckduckgo_search import DDGS
import requests
import os
import uuid
import shutil

def search_images(query: str, max_results: int = 10) -> list[str]:
    """Search for images using DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(
                query,
                max_results=max_results,
            ))
            return [r['image'] for r in results]
    except Exception as e:
        print(f"Search error: {e}")
        return []

def download_image(url: str, save_dir: str) -> str:
    """Download image from URL and save to directory. Returns local filepath."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Guess extension or default to .jpg
        ext = ".jpg"
        if "png" in url.lower(): ext = ".png"
        elif "webp" in url.lower(): ext = ".webp"
        elif "jpeg" in url.lower(): ext = ".jpg"
            
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return filepath
    except Exception as e:
        raise Exception(f"Failed to download image: {str(e)}")
