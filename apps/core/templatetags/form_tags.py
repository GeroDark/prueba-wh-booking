from django import template

register = template.Library()


@register.filter
def accessible(field):
    """Render a form field linked to its help text and errors for screen readers.

    Adds aria-describedby (help + error ids, plus any ids the widget already declares) and
    aria-invalid when the field has errors, so assistive technology reads why a field failed.
    It also hands the field's own error messages to form-feedback.js, so the hints shown while
    typing are the same, translated sentences the server would answer with.
    """
    widget_attrs = field.field.widget.attrs
    messages = field.field.error_messages
    described = [widget_attrs["aria-describedby"]] if widget_attrs.get("aria-describedby") else []
    attrs = {}
    if field.field.required:
        attrs["data-error-required"] = messages["required"]
    if "invalid" in messages and "data-error-invalid" not in widget_attrs:
        attrs["data-error-invalid"] = messages["invalid"]
    if field.help_text:
        described.append(f"{field.auto_id}-help")
    if field.errors:
        described.append(f"{field.auto_id}-error")
        attrs["aria-invalid"] = "true"
    if described:
        attrs["aria-describedby"] = " ".join(described)
    return field.as_widget(attrs=attrs)
