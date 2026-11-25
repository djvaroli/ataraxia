"""Lesson illustrations from English Wikipedia's lead images.

The writer names articles; this adapter looks them up in one Action API request and
keeps only HTTPS images on Wikimedia's image hosts, with the article as the source
link. Anything unexpected drops that illustration; a lesson without images is fine.
"""

import json
import logging
from collections.abc import Callable, Sequence
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ataraxia.domain.lessons import Illustration, IllustrationRequest

logger = logging.getLogger(__name__)

API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "Ataraxia/0.1 (https://github.com/djvaroli/ataraxia; personal learning app)"
IMAGE_HOSTS = frozenset({"upload.wikimedia.org", "thumb.wikimedia.org"})
PAGE_HOST = "en.wikipedia.org"
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 5.0

Fetch = Callable[[str], bytes]


def fetch_url(url: str) -> bytes:
    """GET with a descriptive User-Agent, a timeout, and a response size limit."""
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Wikipedia response too large")
    return body


class _Thumbnail(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str
    width: int | None = None
    height: int | None = None


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    missing: bool = False
    fullurl: str | None = None
    thumbnail: _Thumbnail | None = None


class _Rename(BaseModel):
    """A `normalized` or `redirects` entry: the API renamed `from` to `to`."""

    model_config = ConfigDict(extra="ignore")
    source: str = Field(alias="from")
    target: str = Field(alias="to")


class _Query(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pages: list[_Page] = []
    normalized: list[_Rename] = []
    redirects: list[_Rename] = []


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: _Query = _Query()


class WikipediaIllustrations:
    """`IllustrationResolver` backed by Wikipedia's Action API (`prop=pageimages`)."""

    def __init__(self, fetch: Fetch = fetch_url) -> None:
        self._fetch = fetch

    def resolve(self, requests: Sequence[IllustrationRequest]) -> list[Illustration]:
        if not requests:
            return []
        try:
            body = self._fetch(lookup_url([item.wikipedia_title for item in requests]))
            response = _Response.model_validate(json.loads(body))
        except (URLError, TimeoutError, OSError, ValueError, ValidationError) as error:
            logger.warning("Illustration lookup failed: %s", type(error).__name__)
            return []
        return illustrations_from(response, requests)


def lookup_url(titles: Sequence[str]) -> str:
    query = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "pageimages|info",
        "piprop": "thumbnail",
        "pithumbsize": "1280",
        "pilicense": "any",
        "inprop": "url",
        "redirects": "1",
        "titles": "|".join(titles),
    }
    return f"{API_URL}?{urlencode(query)}"


def illustrations_from(
    response: _Response, requests: Sequence[IllustrationRequest]
) -> list[Illustration]:
    """Match pages back to requested titles (through normalization and redirects)."""
    renames = {item.source: item.target for item in response.query.normalized}
    renames.update({item.source: item.target for item in response.query.redirects})
    pages = {page.title: page for page in response.query.pages}
    found: list[Illustration] = []
    seen: set[str] = set()
    for request in requests:
        title = request.wikipedia_title
        for _ in range(3):  # a title can be normalized and then redirected
            title = renames.get(title, title)
        page = pages.get(title)
        if page is None or page.missing or page.thumbnail is None or page.fullurl is None:
            continue
        image_url = _clean_image_url(page.thumbnail.source)
        if image_url is None or image_url in seen or not _is_page_url(page.fullurl):
            continue
        seen.add(image_url)
        found.append(
            Illustration(
                image_url=image_url,
                page_url=page.fullurl,
                title=page.title,
                caption=request.caption,
                width=page.thumbnail.width,
                height=page.thumbnail.height,
            )
        )
    return found


def _clean_image_url(url: str) -> str | None:
    """Accept only HTTPS Wikimedia image hosts; drop tracking parameters."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in IMAGE_HOSTS:
        return None
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.startswith("utm_")])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _is_page_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname == PAGE_HOST
