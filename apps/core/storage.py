"""Uploaded images on Cloudinary in production (D39).

Render's free disk is wiped on every deploy and restart, so photos uploaded from the admin would
disappear. With CLOUDINARY_URL set, Django stores them on Cloudinary and serves them from its CDN.
The files are already WebP of at most 1200 px when they arrive here (OptimizedImageField), so
Cloudinary stores and delivers them as they are.

A small adapter over the official SDK instead of `django-cloudinary-storage`, which has not been
updated since 2020.
"""

from pathlib import PurePosixPath
from urllib.request import urlopen

import cloudinary
import cloudinary.api
import cloudinary.uploader
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryMediaStorage(Storage):
    """Django storage for images: `properties/loft.webp` lives at `<folder>/properties/loft`."""

    def __init__(self, folder=None):
        self.folder = folder or settings.CLOUDINARY_FOLDER

    def _public_id(self, name):
        path = PurePosixPath(name)
        return str(PurePosixPath(self.folder) / path.with_suffix(""))

    def _format(self, name):
        return PurePosixPath(name).suffix.lstrip(".") or None

    def _save(self, name, content):
        content.seek(0)
        cloudinary.uploader.upload(
            content,
            public_id=self._public_id(name),
            resource_type="image",
            overwrite=False,
        )
        return name

    def _open(self, name, mode="rb"):
        # Read back for the JPEG copies of the e-mail (apps.core.images.email_jpeg).
        with urlopen(self.url(name), timeout=20) as response:  # noqa: S310 (our own CDN URL)
            return ContentFile(response.read(), name=name)

    def exists(self, name):
        try:
            cloudinary.api.resource(self._public_id(name), resource_type="image")
        except cloudinary.exceptions.NotFound:
            return False
        return True

    def url(self, name):
        image = cloudinary.CloudinaryImage(self._public_id(name))
        return image.build_url(format=self._format(name), secure=True)

    def delete(self, name):
        cloudinary.uploader.destroy(self._public_id(name), resource_type="image", invalidate=True)

    def size(self, name):
        return cloudinary.api.resource(self._public_id(name), resource_type="image")["bytes"]
