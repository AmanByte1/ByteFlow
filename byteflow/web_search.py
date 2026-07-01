"""
Free, no-API-key web search via DuckDuckGo's static HTML endpoint
(html.duckduckgo.com) - works without JavaScript, no signup, no key.

This is genuinely more fragile than a real search API: there's no
stable contract, and DuckDuckGo can change their HTML structure or
block requests at any time. Every function here is built to degrade
honestly - on any failure (network error, blocked request, unexpected
HTML), it returns a clear error string rather than crashing or
silently returning nothing.

Uses only the Python standard library (urllib, html.parser) - no new
dependency required, consistent with the rest of ByteFlow.
"""

import re
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser


SEARCH_URL = "https://html.duckduckgo.com/html/"

# A realistic browser User-Agent and the headers a real browser sends
# alongside it - DuckDuckGo (like most sites) is far more likely to
# serve a bot-challenge page instead of real results to a request that
# only sets User-Agent and nothing else a browser would normally send.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_REQUEST_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/",
}

# Substrings that show up on DuckDuckGo's bot-challenge / "unusual
# traffic" interstitial pages rather than a real results page. Checked
# on the raw HTML before parsing, so a block gets reported honestly as
# "search unavailable" instead of silently looking like "no results
# for your query" - those are very different situations and a caller
# should be told which one actually happened.
_BLOCK_PAGE_MARKERS = (
    "anomaly",
    "unusual traffic",
    "problem-solving",
    "if you are seeing this",
)


class WebSearchError(Exception):
    pass


class _ResultParser(HTMLParser):
    """
    Parses html.duckduckgo.com's result markup. In the current markup
    each result title lives in an `<a class="result__a" href="...">`,
    but that class name is not part of any stable contract - DuckDuckGo
    has changed/obfuscated result classes before. To survive that, a
    title link is recognized two ways, either is enough:
      - the classic `class` contains "result__a", OR
      - the href matches DuckDuckGo's redirect-wrapper shape
        ("duckduckgo.com/l/?uddg=..."), which is how DDG wraps every
        real outbound result link regardless of what CSS class it
        currently uses - this is a much more stable signal than a
        class name because it's load-bearing (DDG needs it to track
        clickthroughs), not just presentational.
    The snippet is still matched by class-substring ("result__snippet")
    since there's no similarly stable non-class signal for it; losing
    snippets on a markup change degrades gracefully (empty snippet,
    title/url still present) rather than losing the whole result.
    """

    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._in_title_link = False
        self._in_snippet = False
        self._snippet_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        href = attrs_dict.get("href", "")

        if tag == "a" and ("result__a" in classes or "uddg=" in href):
            self._current = {"title": "", "url": href, "snippet": ""}
            self._in_title_link = True

        elif "result__snippet" in classes:
            self._in_snippet = True
            self._snippet_depth = 1
            if self._current is None:
                self._current = {"title": "", "url": "", "snippet": ""}
        elif self._in_snippet:
            self._snippet_depth += 1

    def handle_endtag(self, tag):
        if tag == "a" and self._in_title_link:
            self._in_title_link = False
        if self._in_snippet:
            self._snippet_depth -= 1
            if self._snippet_depth <= 0:
                self._in_snippet = False
                if self._current is not None:
                    self.results.append(self._current)
                    self._current = None

    def handle_data(self, data):
        if self._in_title_link and self._current is not None:
            self._current["title"] += data
        elif self._in_snippet and self._current is not None:
            self._current["snippet"] += data


def _clean_ddg_redirect_url(url):
    """
    DuckDuckGo's HTML endpoint wraps result URLs in a redirect like
    '//duckduckgo.com/l/?uddg=<encoded real URL>&...'. Extract and
    decode the real target URL; if it's already a plain URL (no
    redirect wrapper), return it unchanged.
    """
    if "uddg=" in url:
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        if "uddg" in query:
            return urllib.parse.unquote(query["uddg"][0])
    return url


def _looks_like_block_page(html):
    """
    True if `html` looks like a DuckDuckGo bot-challenge/anomaly page
    rather than a normal results page. Checked on a lowercased slice of
    the body so this stays cheap on large pages.
    """
    sample = html[:5000].lower()
    return any(marker in sample for marker in _BLOCK_PAGE_MARKERS)


def search(query, max_results=5, timeout=10):
    """
    Search the web via DuckDuckGo's HTML endpoint. Returns a list of
    dicts: [{"title": ..., "url": ..., "snippet": ...}, ...], up to
    max_results entries. Returns an empty list if there are genuinely
    no results. Raises WebSearchError with a clear message on network
    failure, if DuckDuckGo serves a bot-challenge page instead of
    results, or if the response can't be parsed at all - callers
    should catch this and degrade gracefully (see agent.py's
    web_search tool). This distinction matters: "genuinely no results"
    and "the request got blocked" look identical to a naive caller
    unless blocking is detected explicitly, which is what
    _looks_like_block_page() is for.
    """
    if not query or not query.strip():
        return []

    params = urllib.parse.urlencode({"q": query})
    url = f"{SEARCH_URL}?{params}"

    request = urllib.request.Request(url, headers=_REQUEST_HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise WebSearchError(
            f"Search request failed with HTTP {e.code}. "
            f"DuckDuckGo may be rate-limiting or blocking this request."
        ) from e
    except urllib.error.URLError as e:
        raise WebSearchError(
            f"Could not reach the search engine: {e.reason}. "
            f"Check your internet connection."
        ) from e
    except TimeoutError as e:
        raise WebSearchError(f"Search request timed out after {timeout}s.") from e

    if _looks_like_block_page(html):
        raise WebSearchError(
            "DuckDuckGo returned a bot-detection/anomaly page instead of "
            "results for this request - it's blocking automated traffic "
            "from this network right now, not reporting a genuine "
            "zero-result search. Waiting a bit before retrying, or "
            "switching networks, usually resolves this."
        )

    parser = _ResultParser()
    try:
        parser.feed(html)
    except Exception as e:
        raise WebSearchError(
            f"Could not parse search results - the search engine's page "
            f"structure may have changed. ({e})"
        ) from e

    results = []
    for r in parser.results:
        title = re.sub(r"\s+", " ", r["title"]).strip()
        snippet = re.sub(r"\s+", " ", r["snippet"]).strip()
        url_clean = _clean_ddg_redirect_url(r["url"])
        if title and url_clean:
            results.append({"title": title, "url": url_clean, "snippet": snippet})
        if len(results) >= max_results:
            break

    return results


def search_formatted(query, max_results=5, timeout=10):
    """
    Convenience wrapper: search() and format the results as a single
    readable text block, ready to paste into an LLM prompt. Returns a
    clear message (not an exception) if the search fails or finds
    nothing - safe to call directly from prompt-building code.
    """
    try:
        results = search(query, max_results=max_results, timeout=timeout)
    except WebSearchError as e:
        return f"[Web search unavailable: {e}]"

    if not results:
        return f"[No web search results found for: {query}]"

    lines = [f"Web search results for \"{query}\":"]
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r['title']}")
        if r["snippet"]:
            lines.append(f"   {r['snippet']}")
        lines.append(f"   {r['url']}")
    return "\n".join(lines)
