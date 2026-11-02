"""Web tools: search, fetch, and optional JavaScript rendering.

Fetches refuse loopback, private, link-local, and reserved addresses by
default (including after redirects) so a page cannot steer the agent into the
local network. An optional domain allowlist narrows access further.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from agentic.config import NetworkConfig
from agentic.tools.base import Tool, ToolContext, ToolError, schema

USER_AGENT = (
    "Mozilla/5.0 (compatible; AgenticBot/0.2; +https://github.com/divyanshu-iitian/Agentic)"
)
MAX_DOWNLOAD_BYTES = 3_000_000
MAX_REDIRECTS = 5
# Small models request tiny pages and miss the content they need.
MIN_PAGE_CHARS = 2_000
SCHEME_ONLY = re.compile(r"^[a-z][a-z0-9+.-]*:(?!\d)", re.IGNORECASE)
BLOCK_TAGS = {"script", "style", "noscript", "svg", "template", "iframe", "head"}
BREAK_TAGS = {
    "p",
    "div",
    "br",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "pre",
    "blockquote",
    "table",
    "ul",
    "ol",
}


def check_url(url: str, network: NetworkConfig) -> str:
    url = url.strip()
    # "javascript:x" or "data:x" without "//" is a scheme, while "host:8080" is a port.
    if "://" not in url and SCHEME_ONLY.match(url):
        raise ToolError("Only http and https URLs are allowed")
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in {"http", "https"}:
        raise ToolError("Only http and https URLs are allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ToolError("URL has an invalid port") from exc
    host = (parsed.hostname or "").casefold()
    if not host:
        raise ToolError("URL has no hostname")
    if network.allowed_domains and not any(
        host == domain.casefold().lstrip(".") or host.endswith("." + domain.casefold().lstrip("."))
        for domain in network.allowed_domains
    ):
        raise ToolError(f"Domain {host} is not in network.allowed_domains")
    if not network.allow_private_hosts:
        try:
            infos = socket.getaddrinfo(host, port or None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise ToolError(f"Cannot resolve {host}") from exc
        for info in infos:
            address = ipaddress.ip_address(info[4][0].split("%", 1)[0])
            if not address.is_global:
                raise ToolError(f"{host} resolves to a non-public address ({address}); refused")
    return parsed.geturl()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._blocked = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            self._blocked += 1
        elif tag in BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS and self._blocked:
            self._blocked -= 1
        elif tag in BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._blocked:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(line for line in lines if line)
    return " ".join(parser.title.split()), text


def fetch(url: str, network: NetworkConfig, session: requests.Session | None = None):
    session = session or requests.Session()
    current = check_url(url, network)
    for _ in range(MAX_REDIRECTS + 1):
        response = session.get(
            current,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
            allow_redirects=False,
            stream=True,
        )
        if response.is_redirect and response.headers.get("location"):
            current = check_url(urljoin(current, response.headers["location"]), network)
            response.close()
            continue
        chunks, size = [], 0
        for chunk in response.iter_content(65_536):
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_DOWNLOAD_BYTES:
                break
        response.close()
        body = b"".join(chunks)
        encoding = response.encoding or "utf-8"
        return (
            current,
            response.status_code,
            response.headers.get("content-type", ""),
            body.decode(encoding, errors="replace"),
        )
    raise ToolError("Too many redirects")


def http_fetch(args: dict[str, Any], ctx: ToolContext) -> str:
    network = ctx.runtime.settings.network
    final_url, status, content_type, body = fetch(args["url"], network)
    if "html" in content_type or body.lstrip()[:15].lower().startswith(("<!doctype", "<html")):
        title, text = html_to_text(body)
    else:
        title, text = "", body
    limit = max(MIN_PAGE_CHARS, int(args.get("max_chars", 8_000)))
    header = f"URL: {final_url}\nStatus: {status}\n" + (f"Title: {title}\n" if title else "")
    return f"{header}\n{text[:limit]}"


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._field: str | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            href = attributes.get("href") or ""
            target = parse_qs(urlparse(href).query).get("uddg", [href])[0]
            self.results.append({"title": "", "url": target, "snippet": ""})
            self._field = "title"
        elif "result__snippet" in classes and self.results:
            self._field = "snippet"

    def handle_endtag(self, tag):
        if tag in {"a", "td", "div"}:
            self._field = None

    def handle_data(self, data):
        if self._field and self.results:
            self.results[-1][self._field] += data


def web_search(args: dict[str, Any], ctx: ToolContext) -> str:
    """Best-effort search through DuckDuckGo's HTML endpoint (no API key)."""
    network = ctx.runtime.settings.network
    _, status, _, body = fetch(
        "https://html.duckduckgo.com/html/?" + requests.compat.urlencode({"q": args["query"]}),
        network,
    )
    if status != 200:
        raise ToolError(f"Search returned HTTP {status}; try http_fetch on a known site")
    parser = _DuckDuckGoParser()
    parser.feed(body)
    limit = int(args.get("max_results", 6))
    results = [r for r in parser.results if r["url"].startswith("http")][:limit]
    if not results:
        return "No results (the search page may have changed or rate-limited the request)."
    return "\n\n".join(
        f"{i}. {' '.join(r['title'].split())}\n   {r['url']}\n   {' '.join(r['snippet'].split())}"
        for i, r in enumerate(results, 1)
    )


def browser_render(args: dict[str, Any], ctx: ToolContext) -> str:
    """Render a JavaScript-heavy page with Playwright and return its text."""
    network = ctx.runtime.settings.network
    url = check_url(args["url"], network)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ToolError(
            "Playwright is not installed: pip install playwright && playwright install chromium"
        ) from exc

    checked_hosts: dict[str, bool] = {}

    def guard(route, request):
        # Apply the same host policy to redirects and every subresource.
        parsed = urlparse(request.url)
        if parsed.scheme in {"data", "blob", "about"}:
            return route.continue_()
        host = parsed.hostname or ""
        if host not in checked_hosts:
            try:
                check_url(request.url, network)
                checked_hosts[host] = True
            except ToolError:
                checked_hosts[host] = False
        return route.continue_() if checked_hosts[host] else route.abort()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.route("**/*", guard)
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(int(args.get("wait_ms", 1500)))
            title = page.title()
            text = page.inner_text("body")
        finally:
            browser.close()
    limit = max(MIN_PAGE_CHARS, int(args.get("max_chars", 8_000)))
    return f"URL: {url}\nTitle: {title}\n\n{text[:limit]}"


def web_tools() -> list[Tool]:
    return [
        Tool(
            "web_search",
            "Search the web. Returns titles, URLs, and snippets. Fetch pages for details.",
            schema(
                {
                    "query": {"type": "string", "maxLength": 400},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 15},
                },
                ["query"],
            ),
            "network",
            web_search,
        ),
        Tool(
            "http_fetch",
            "Download a public web page or API response and return readable text.",
            schema(
                {
                    "url": {"type": "string", "maxLength": 2048},
                    "max_chars": {"type": "integer", "minimum": 2_000, "maximum": 50_000},
                },
                ["url"],
            ),
            "network",
            http_fetch,
        ),
        Tool(
            "browser_render",
            "Open a page in headless Chromium (for JavaScript sites) and return its text.",
            schema(
                {
                    "url": {"type": "string", "maxLength": 2048},
                    "wait_ms": {"type": "integer", "minimum": 0, "maximum": 15_000},
                    "max_chars": {"type": "integer", "minimum": 2_000, "maximum": 50_000},
                },
                ["url"],
            ),
            "network",
            browser_render,
            timeout=120,
        ),
    ]
