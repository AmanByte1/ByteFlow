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

# A realistic browser User-Agent - DuckDuckGo (like most sites) blocks
# requests that look like bare scripts with no User-Agent at all.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class WebSearchError(Exception):
    pass


class _ResultParser(HTMLParser):
    """
    Parses html.duckduckgo.com's result markup. Each result lives in a
    `<div class="result results_links ...">` containing:
      - an `<a class="result__a" href="...">title text</a>`
      - an element with class containing "result__snippet" for the snippet

    This is intentionally tolerant: if DuckDuckGo's markup shifts
    slightly (extra classes, nesting changes), the class-substring
    checks below (`"result__a" in classes`) are more likely to keep
    working than an exact CSS-selector match would be. If the structure
    changes enough to break this entirely, search() returns an empty
    list / honest error rather than garbage results - see search().
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

        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": attrs_dict.get("href", ""), "snippet": ""}
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


def search(query, max_results=5, timeout=10):
    """
    Search the web via DuckDuckGo's HTML endpoint. Returns a list of
    dicts: [{"title": ..., "url": ..., "snippet": ...}, ...], up to
    max_results entries. Returns an empty list if there are genuinely
    no results. Raises WebSearchError with a clear message on network
    failure or if the response can't be parsed at all - callers should
    catch this and degrade gracefully (see agent.py's web_search tool).
    """
    if not query or not query.strip():
        return []

    params = urllib.parse.urlencode({"q": query})
    url = f"{SEARCH_URL}?{params}"

    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

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
