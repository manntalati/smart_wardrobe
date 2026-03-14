"""
Centralised path configuration for the Smart Wardrobe backend.
Import from here instead of re-deriving paths in each module.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, "thumbnails")
