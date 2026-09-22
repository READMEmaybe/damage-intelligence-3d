"""Evidence helpers: record the source phrase behind every decision (brief §11)."""

from __future__ import annotations

import re

from .ontology import ZONES_LONGEST_FIRST

_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase + collapse whitespace. Keeps umlauts; handles ß->ss later if needed."""
    return _WS_RE.sub(" ", text.lower()).strip()


def find_zone_mentions(text: str) -> dict[str, str]:
    """Longest-match-first zone detection with masking.

    Returns {zone: matched verbatim phrase}. Masking prevents a child zone
    ("Stoßstange vorne links") from also firing its parent ("Stoßstange
    vorne") and vice versa. Matching is case-insensitive substring based,
    mirroring how the corpus names zones.
    """
    work = normalize(text)
    mentions: dict[str, str] = {}
    for zone in ZONES_LONGEST_FIRST:
        needle = normalize(zone)
        idx = work.find(needle)
        if idx == -1:
            continue
        mentions[zone] = needle
        work = work[:idx] + "~" * len(needle) + work[idx + len(needle):]
    return mentions


def find_phrase(text: str, phrase: str) -> str | None:
    """Return the verbatim substring for a normalized phrase, or None."""
    ntext, nphrase = normalize(text), normalize(phrase)
    idx = ntext.find(nphrase)
    if idx == -1:
        return None
    return text[idx : idx + len(nphrase)]
