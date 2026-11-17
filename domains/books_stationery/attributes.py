import re


def extract(text):
    value = str(text or "")
    lower = value.lower()
    attrs = {}
    match = re.search(r"\b(\d{9}[\dXx]|\d{13})\b", value)
    if match: attrs["isbn"] = match.group(1).upper()
    match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+edition\b", lower)
    if match: attrs["edition"] = int(match.group(1))
    for language in ("english", "hindi", "marathi", "tamil", "telugu", "bengali", "gujarati", "kannada", "malayalam"):
        if re.search(rf"\b{language}\b", lower): attrs["language"] = language; break
    for binding in ("paperback", "hardcover", "spiral bound", "ebook", "kindle edition", "audiobook"):
        if binding in lower: attrs["format"] = binding; break
    match = re.search(r"\bpack\s+of\s+(\d+)\b|\b(\d+)\s*(?:pieces|pcs|pack)\b", lower)
    if match: attrs["pack_quantity"] = int(next(x for x in match.groups() if x))
    for exam in ("jee advanced", "jee main", "neet", "upsc", "gate", "mpsc", "cat", "clat", "ssc", "banking"):
        if re.search(rf"(?<![a-z0-9]){re.escape(exam)}(?![a-z0-9])", lower): attrs["exam"] = exam; break
    for kind in ("ballpoint", "ball pen", "fountain pen", "gel pen", "rollerball", "marker", "highlighter"):
        if kind in lower:
            attrs["writing_type"] = "ballpoint" if kind == "ball pen" else "fountain" if kind == "fountain pen" else "gel" if kind == "gel pen" else kind
            break
    if re.search(r"\bscientific\s+calculator\b", lower): attrs["calculator_type"] = "scientific"
    elif re.search(r"\bbasic\s+calculator\b", lower): attrs["calculator_type"] = "basic"
    match = re.search(r"\b(\d{2,4})\s*(?:pages|page)\b", lower)
    if match: attrs["page_count"] = int(match.group(1))
    return attrs
