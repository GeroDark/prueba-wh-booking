from django.conf import settings
from django.db import models
from django.db.models.fields.files import ImageFieldFile

from .images import optimize_image


class OptimizedImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        # Every write goes through here: uploads committed by the model's pre_save
        # (admin, forms, seed command) and direct calls to `instance.image.save(...)`.
        name, content = optimize_image(
            content,
            name,
            max_dimension=self.field.max_dimension,
            quality=self.field.quality,
        )
        super().save(name, content, save)


class OptimizedImageField(models.ImageField):
    """ImageField that stores every upload as WebP, resized to fit IMAGE_MAX_DIMENSION.

    Limits default to the project settings, read when the image is saved
    (so they are not frozen into migrations).
    """

    attr_class = OptimizedImageFieldFile

    def __init__(self, *args, max_dimension=None, quality=None, **kwargs):
        self._max_dimension = max_dimension
        self._quality = quality
        super().__init__(*args, **kwargs)

    @property
    def max_dimension(self):
        return self._max_dimension or settings.IMAGE_MAX_DIMENSION

    @property
    def quality(self):
        return self._quality or settings.IMAGE_WEBP_QUALITY

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self._max_dimension:
            kwargs["max_dimension"] = self._max_dimension
        if self._quality:
            kwargs["quality"] = self._quality
        return name, path, args, kwargs
