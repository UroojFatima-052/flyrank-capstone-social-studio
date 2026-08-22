import pytest

from app.services.fetcher import FetchError, fetch_page


def test_fetch_rejects_unreachable_host():
    with pytest.raises(FetchError):
        fetch_page("https://this-domain-does-not-exist-12345.example")