import unicodedata
from collections.abc import Iterable

from app.core.exceptions import ContentBlockedError


def ensure_content_allowed(texts: Iterable[str], blocked_terms: Iterable[str]) -> None:
    terms = tuple(
        unicodedata.normalize("NFKC", term).casefold()
        for term in blocked_terms
        if term.strip()
    )
    for text in texts:
        normalized_text = unicodedata.normalize("NFKC", text).casefold()
        if any(term in normalized_text for term in terms):
            raise ContentBlockedError()
