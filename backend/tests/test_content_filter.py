import pytest

from app.core.exceptions import ContentBlockedError
from app.utils.content_filter import ensure_content_allowed


def test_content_filter_matches_case_insensitively_and_normalizes_unicode():
    with pytest.raises(ContentBlockedError):
        ensure_content_allowed(["ＳＴＯＰ"], ["stop"])


def test_content_filter_allows_unmatched_terms():
    ensure_content_allowed(["Learn something new."], ["blocked phrase"])
