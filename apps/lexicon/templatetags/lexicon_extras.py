from django import template

register = template.Library()


@register.filter
def definition_first_line_preview(text, max_chars=127):
    """First non-empty line of definition content, truncated for list cards."""
    if text is None:
        return ""
    try:
        limit = int(max_chars)
    except (TypeError, ValueError):
        limit = 127
    for line in str(text).splitlines():
        stripped = line.strip()
        if stripped:
            if len(stripped) > limit:
                return stripped[:limit].rstrip() + "…"
            return stripped
    return ""
