"""
Image search service using DuckDuckGo.
"""
from ddgs import DDGS
import requests
import os
import uuid
import shutil

import re
import json

def search_images_fallback(query: str, max_results: int = 10) -> list[str]:
    """Fallback search using requests directly."""
    print(f"Attempting fallback search for: {query}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # 1. Get VQD
        resp = requests.get(f"https://duckduckgo.com/?q={query}&t=h_&iax=images&ia=images", headers=headers, timeout=10)
        resp.raise_for_status()
        vqd_match = re.search(r'vqd=([\'"]?)([\d-]+)\1', resp.text)
        if not vqd_match:
            print("Fallback: Could not find VQD")
            return []
        vqd = vqd_match.group(2)

        # 2. Get Images
        params = {
            "l": "us-en",
            "o": "json",
            "q": query,
            "vqd": vqd,
            "f": ",,,",
            "p": "1"
        }
        resp = requests.get("https://duckduckgo.com/i.js", params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return [r["image"] for r in results[:max_results]]
    except Exception as e:
        print(f"Fallback search error: {e}")
        return []

def search_images(query: str, max_results: int = 10) -> list[str]:
    """Search for images using DuckDuckGo with fallback."""
    images = []
    try:
        # Revert to default, try/except will handle errors
        with DDGS(timeout=20) as ddgs:
            results = list(ddgs.images(
                query,
                max_results=max_results,
            ))
            images = [r['image'] for r in results]
    except Exception as e:
        print(f"DDGS error: {e}")
    
    if not images:
        images = search_images_fallback(query, max_results)

    if not images:
        # Final fallback for demo purposes
        return [
            "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=500",
            "https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=500",
            "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=500",
            "https://images.unsplash.com/photo-1550418290-a8d86ad674a6?w=500",
            "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500"
        ]
    
    return images

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
