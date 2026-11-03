def existing_marker():
    return "keep-me"


def normalize_tags(tags):
    """Return nonempty, stripped lowercase tags in input order."""
    normalized = []
    for tag in tags:
        tag = tag.strip().lower()
        if tag:
            normalized.append(tag)
    return normalized


def unique_tags(tags):
    """Return the first occurrence of each normalized tag in input order."""
    seen = set()
    unique = []
    for tag in normalize_tags(tags):
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return unique
