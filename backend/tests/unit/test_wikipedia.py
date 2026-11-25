"""Illustrations keep only Wikimedia-hosted images matched to the requested articles."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ataraxia.adapters.wikipedia import WikipediaIllustrations, lookup_url
from ataraxia.domain.lessons import IllustrationRequest

FIXTURE = Path(__file__).parents[1] / "fixtures" / "wikipedia" / "pageimages.json"


def request(title: str) -> IllustrationRequest:
    return IllustrationRequest(wikipedia_title=title, caption=f"About {title}")


def test_resolves_through_normalization_and_redirects_in_request_order() -> None:
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return FIXTURE.read_bytes()

    resolver = WikipediaIllustrations(fetch)
    titles = ["The Godfather", "Nonexistent page xyz", "hasegawa Tōhaku", "Muqi Fachang"]
    found = resolver.resolve([request(title) for title in titles])

    assert [item.title for item in found] == ["The Godfather", "Hasegawa Tōhaku", "Muqi"]
    assert [item.caption for item in found] == [
        "About The Godfather",
        "About hasegawa Tōhaku",
        "About Muqi Fachang",
    ]
    assert all(item.page_url.startswith("https://en.wikipedia.org/wiki/") for item in found)
    assert all("utm_" not in item.image_url for item in found)
    assert {urlsplit(item.image_url).hostname for item in found} == {
        "upload.wikimedia.org",
        "thumb.wikimedia.org",
    }
    assert len(fetched) == 1
    query = parse_qs(urlsplit(fetched[0]).query)
    assert query["pilicense"] == ["any"]
    assert query["titles"] == ["|".join(titles)]


def test_rejects_images_outside_wikimedia_and_duplicates() -> None:
    body = {
        "query": {
            "pages": [
                {
                    "title": "Elsewhere",
                    "fullurl": "https://en.wikipedia.org/wiki/Elsewhere",
                    "thumbnail": {"source": "https://evil.example/x.jpg"},
                },
                {
                    "title": "Plain HTTP",
                    "fullurl": "https://en.wikipedia.org/wiki/Plain_HTTP",
                    "thumbnail": {"source": "http://upload.wikimedia.org/x.jpg"},
                },
                {
                    "title": "Good",
                    "fullurl": "https://en.wikipedia.org/wiki/Good",
                    "thumbnail": {"source": "https://upload.wikimedia.org/good.jpg"},
                },
                {
                    "title": "Same image",
                    "fullurl": "https://en.wikipedia.org/wiki/Same_image",
                    "thumbnail": {"source": "https://upload.wikimedia.org/good.jpg"},
                },
                {
                    "title": "Odd page",
                    "fullurl": "https://evil.example/wiki/Odd_page",
                    "thumbnail": {"source": "https://upload.wikimedia.org/odd.jpg"},
                },
            ]
        }
    }
    resolver = WikipediaIllustrations(lambda _url: json.dumps(body).encode())
    titles = ["Elsewhere", "Plain HTTP", "Good", "Same image", "Odd page"]
    assert [item.title for item in resolver.resolve([request(t) for t in titles])] == ["Good"]


def test_failures_return_no_illustrations() -> None:
    def fail(_url: str) -> bytes:
        raise TimeoutError

    assert WikipediaIllustrations(fail).resolve([request("Anything")]) == []
    assert WikipediaIllustrations(lambda _url: b"not json").resolve([request("A")]) == []
    assert WikipediaIllustrations(lambda _url: b"{}").resolve([]) == []


def test_lookup_url_is_https_wikipedia() -> None:
    url = urlsplit(lookup_url(["A", "B"]))
    assert (url.scheme, url.hostname, url.path) == ("https", "en.wikipedia.org", "/w/api.php")
