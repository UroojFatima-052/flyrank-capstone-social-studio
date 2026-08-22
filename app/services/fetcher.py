import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
MAX_BYTES = 2_000_000
USER_AGENT = "SocialMediaStudio/0.1 (capstone project)"


class FetchError(Exception):
    pass


def fetch_page(url: str) -> tuple[str, str]:
    try:
        response = httpx.get(
            url,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise FetchError(f"Page returned {exc.response.status_code}.") from exc
    except httpx.RequestError as exc:
        raise FetchError(f"Could not reach the page: {exc}") from exc

    if len(response.content) > MAX_BYTES:
        raise FetchError("Page is too large to process.")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title and soup.h1:
        title = soup.h1.get_text(strip=True)
    if not title:
        first_line = text.split("\n", 1)[0]
        title = first_line[:120] if first_line else url

    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)
    text = "\n".join(line for line in text.splitlines() if line.strip())

    if len(text) < 200:
        raise FetchError("Could not extract enough text from the page.")

    return title, text