from modeltranslation.translator import TranslationOptions, register

from .models import BookingLine


@register(BookingLine)
class BookingLineTranslation(TranslationOptions):
    # Frozen in both languages, so the confirmation and the e-mail can use either one.
    fields = ("label",)
