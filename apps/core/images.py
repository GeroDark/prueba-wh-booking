import hashlib
from io import BytesIO
from pathlib import PurePath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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


def email_jpeg(field_file, width, height=None, quality=82):
    """URL of a JPEG copy of an uploaded image, for e-mails.

    The site stores WebP (requirement 8), but about a quarter of e-mail clients (Outlook for
    Windows among them) do not show it. The copy is made the first time it is needed and reused
    afterwards; it lives in the same storage as the original (local media or the CDN).
    With `height`, the image is cropped to exactly width x height from its centre.
    """
    key = hashlib.sha1(f"{field_file.name}:{width}:{height}".encode()).hexdigest()[:16]
    name = f"email/{PurePath(field_file.name).stem}-{key}.jpg"
    if not default_storage.exists(name):
        with field_file.open("rb") as source, Image.open(source) as image:
            if height:
                image = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS)
            else:
                image.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
        name = default_storage.save(name, ContentFile(buffer.getvalue()))
    return default_storage.url(name)
