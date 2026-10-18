from io import BytesIO
from pathlib import PurePath

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimize_image(content, name, *, max_dimension, quality):
    """Convert an image to WebP that fits in a `max_dimension` square, keeping its aspect ratio.

    - Applies the EXIF orientation first, so phone photos are not stored sideways.
    - Only shrinks: smaller images keep their size.
    - Keeps transparency when the source has it.

    Returns the new file name (same stem, `.webp` extension) and its content.
    """
    content.seek(0)
    with Image.open(content) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        image = image.convert("RGBA" if _has_alpha(image) else "RGB")
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=quality, method=6)
    return f"{PurePath(name).stem}.webp", ContentFile(buffer.getvalue())


def _has_alpha(image):
    return image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
