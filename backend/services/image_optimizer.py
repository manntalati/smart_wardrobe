"""
Image optimization for uploaded clothing photos.
Resizes to display (max 800px) and thumbnail (max 256px) sizes,
strips EXIF data, and saves as JPEG before CLIP inference.
"""
import os
import logging
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


def optimize_image(source_path: str, stem: str, upload_dir: str, thumbnail_dir: str) -> dict:
    """
    Convert a raw uploaded image to optimised JPEG at two sizes.

    - Display version: max 800×800px, JPEG quality 85, saved to upload_dir/{stem}.jpg
    - Thumbnail:       max 256×256px, JPEG quality 80, saved to thumbnail_dir/{stem}.jpg

    EXIF is stripped implicitly by converting to RGB and re-saving without
    passing the exif kwarg.

    The source file is removed if it differs from the display output path
    (i.e., the original had a non-jpg extension).

    Returns a dict with display_path, thumbnail_path, display_filepath,
    thumbnail_filepath — paths/filepaths callers need.
    """
    display_filename = f"{stem}.jpg"
    display_filepath = os.path.join(upload_dir, display_filename)
    thumb_filepath = os.path.join(thumbnail_dir, display_filename)

    img = Image.open(source_path).convert("RGB")

    # Display version — shrink only, preserve aspect ratio
    display_img = ImageOps.contain(img, (800, 800))
    display_img.save(display_filepath, "JPEG", quality=85, optimize=True)

    # Thumbnail
    thumb_img = ImageOps.contain(img, (256, 256))
    thumb_img.save(thumb_filepath, "JPEG", quality=80, optimize=True)

    # Clean up raw source if it's a different file (different extension)
    if os.path.abspath(source_path) != os.path.abspath(display_filepath):
        try:
            os.remove(source_path)
        except OSError:
            logger.warning("Could not remove temp upload file: %s", source_path)

    logger.debug("Optimised: %s + thumbnail", display_filepath)
    return {
        "display_path": f"/uploads/{display_filename}",
        "thumbnail_path": f"/uploads/thumbnails/{display_filename}",
        "display_filepath": display_filepath,
        "thumbnail_filepath": thumb_filepath,
    }
