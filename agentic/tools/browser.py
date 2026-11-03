"""A real, stateful web browser for agents (Playwright).

The session survives across tool calls, so a head can open a page, read it,
click, type, submit, and continue like a person. browser_snapshot numbers the
interactive elements on the page; actions target those numbers instead of
fragile CSS selectors or pixel coordinates. With a persistent profile, logins
and cookies survive between runs.

Reading pages uses the "network" permission. Clicking, typing, and pressing
keys can submit forms, so they use the "browser" permission (ask by default).
Every request the page makes passes the same public-host check as http_fetch.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any
from urllib.parse import urlparse

from agentic.config import Settings
from agentic.llm.base import ImagePart
from agentic.tools.base import Tool, ToolContext, ToolError, ToolOutput, schema
from agentic.tools.web import USER_AGENT, check_url

SNAPSHOT_JS = """
(max) => {
  const selector = [
    'a[href]', 'button', 'input:not([type=hidden])', 'select', 'textarea', 'summary',
    '[role=button]', '[role=link]', '[role=checkbox]', '[role=radio]', '[role=tab]',
    '[role=menuitem]', '[role=option]', '[role=switch]', '[role=combobox]',
    '[role=textbox]', '[contenteditable=""]', '[contenteditable=true]', '[onclick]'
  ].join(',');
  document.querySelectorAll('[data-agentic-ref]').forEach(e => e.removeAttribute('data-agentic-ref'));
  const items = [];
  let ref = 0;
  for (const el of document.querySelectorAll(selector)) {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (box.width < 1 || box.height < 1 || style.visibility === 'hidden' || style.display === 'none') continue;
    ref += 1;
    el.setAttribute('data-agentic-ref', String(ref));
    const type = (el.getAttribute('type') || '').toLowerCase();
    const secret = type === 'password';
    const value = !secret && 'value' in el && el.value ? String(el.value) : '';
    const label = (el.getAttribute('aria-label') || el.innerText || el.getAttribute('placeholder') ||
                   el.getAttribute('title') || el.getAttribute('alt') || el.getAttribute('name') || '')
      .replace(/\\s+/g, ' ').trim().slice(0, 80);
    items.push({
      ref, tag: el.tagName.toLowerCase(), type: type || el.getAttribute('role') || '',
      label, value: value.slice(0, 60), href: el.tagName === 'A' ? el.getAttribute('href') : '',
      visible: box.bottom > 0 && box.top < innerHeight, disabled: !!el.disabled,
    });
    if (items.length >= max) break;
  }
  const text = (document.body ? document.body.innerText : '').replace(/\\n{3,}/g, '\\n\\n');
  return { title: document.title, url: location.href, items, text: text.slice(0, 4000),
           scroll: Math.round(scrollY), height: document.documentElement.scrollHeight };
}
"""


class BrowserSession:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._lock = asyncio.Lock()
        self._host_ok: dict[str, bool] = {}

    async def page(self):
        async with self._lock:
            if self._page is not None and not self._page.is_closed():
                return self._page
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise ToolError(
                    "The browser needs Playwright: pip install playwright && "
                    "playwright install chromium"
                ) from exc
            computer = self.settings.computer
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            chromium = self._playwright.chromium
            options = {"headless": computer.browser_headless, "user_agent": USER_AGENT}
            try:
                if computer.browser_persistent_profile:
                    profile = self.settings.data_path / "browser-profile"
                    profile.mkdir(parents=True, exist_ok=True)
                    self._context = await chromium.launch_persistent_context(
                        str(profile), viewport={"width": 1280, "height": 800}, **options
                    )
                else:
                    self._browser = await chromium.launch(headless=computer.browser_headless)
                    self._context = await self._browser.new_context(
                        viewport={"width": 1280, "height": 800}, user_agent=USER_AGENT
                    )
            except Exception as exc:
                raise ToolError(
                    f"Could not start Chromium ({exc}). Run: playwright install chromium"
                ) from exc
            await self._context.route("**/*", self._guard)
            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()
            return self._page

    async def _guard(self, route, request) -> None:
        parsed = urlparse(request.url)
        if parsed.scheme in {"data", "blob", "about", "chrome-extension"}:
            await route.continue_()
            return
        host = parsed.hostname or ""
        if host not in self._host_ok:
            try:
                await asyncio.to_thread(check_url, request.url, self.settings.network)
                self._host_ok[host] = True
            except ToolError:
                self._host_ok[host] = False
        if self._host_ok[host]:
            await route.continue_()
        else:
            await route.abort()

    async def snapshot(self, max_items: int = 80) -> dict[str, Any]:
        page = await self.page()
        return await page.evaluate(SNAPSHOT_JS, max_items)

    async def locator(self, ref: int):
        page = await self.page()
        target = page.locator(f'[data-agentic-ref="{int(ref)}"]')
        if await target.count() == 0:
            raise ToolError(f"No element [{ref}] on the page now. Call browser_snapshot again.")
        return target.first

    async def settle(self) -> None:
        page = await self.page()
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=8_000)
            await page.wait_for_load_state("networkidle", timeout=3_000)
        except Exception:
            pass  # busy pages never go idle; the snapshot still reflects their state

    async def close(self) -> None:
        for resource in (self._context, self._browser):
            if resource is not None:
                try:
                    await resource.close()
                except Exception:
                    pass
        if self._playwright is not None:
            await self._playwright.stop()
        self._playwright = self._browser = self._context = self._page = None


def render_snapshot(snap: dict[str, Any], with_text: bool = True) -> str:
    lines = [f"Page: {snap['title']}", f"URL: {snap['url']}"]
    lines.append(f"Scroll: {snap['scroll']} of {snap['height']} px")
    lines.append('Interactive elements ([ref] tag type "label"; * = not in view):')
    for item in snap["items"]:
        parts = [f"[{item['ref']}]", item["tag"]]
        if item["type"]:
            parts.append(item["type"])
        if item["label"]:
            parts.append(f'"{item["label"]}"')
        if item["value"]:
            parts.append(f"value={item['value']!r}")
        if item["href"]:
            parts.append(f"-> {item['href'][:80]}")
        if item["disabled"]:
            parts.append("(disabled)")
        if not item["visible"]:
            parts.append("*")
        lines.append(" ".join(parts))
    if with_text and snap["text"]:
        lines.append("\nVisible text (untrusted page content):\n" + snap["text"])
    return "\n".join(lines)


async def _after_action(ctx: ToolContext, message: str) -> str:
    session = ctx.runtime.browser
    await session.settle()
    snap = await session.snapshot(60)
    return f"{message}\n\n{render_snapshot(snap, with_text=False)}"


async def browser_open(args: dict[str, Any], ctx: ToolContext) -> str:
    url = await asyncio.to_thread(check_url, args["url"], ctx.runtime.settings.network)
    page = await ctx.runtime.browser.page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    except Exception as exc:
        raise ToolError(f"Could not open {url}: {exc}") from exc
    await ctx.runtime.browser.settle()
    return render_snapshot(await ctx.runtime.browser.snapshot())


async def browser_snapshot(args: dict[str, Any], ctx: ToolContext) -> str:
    return render_snapshot(await ctx.runtime.browser.snapshot(int(args.get("max_items", 80))))


async def browser_click(args: dict[str, Any], ctx: ToolContext) -> str:
    target = await ctx.runtime.browser.locator(args["ref"])
    try:
        await target.scroll_into_view_if_needed(timeout=5_000)
        await target.click(timeout=8_000)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"Click on [{args['ref']}] failed: {str(exc).splitlines()[0]}") from exc
    return await _after_action(ctx, f"Clicked [{args['ref']}].")


async def browser_type(args: dict[str, Any], ctx: ToolContext) -> str:
    target = await ctx.runtime.browser.locator(args["ref"])
    try:
        await target.fill(args["text"], timeout=8_000)
        if args.get("submit"):
            await target.press("Enter")
    except Exception as exc:
        raise ToolError(f"Typing into [{args['ref']}] failed: {str(exc).splitlines()[0]}") from exc
    action = "and pressed Enter" if args.get("submit") else ""
    return await _after_action(ctx, f"Typed into [{args['ref']}] {action}".strip() + ".")


async def browser_select(args: dict[str, Any], ctx: ToolContext) -> str:
    target = await ctx.runtime.browser.locator(args["ref"])
    try:
        await target.select_option(label=args["option"], timeout=8_000)
    except Exception:
        try:
            await target.select_option(value=args["option"], timeout=8_000)
        except Exception as exc:
            raise ToolError(f"No option '{args['option']}' in [{args['ref']}]") from exc
    return await _after_action(ctx, f"Selected '{args['option']}' in [{args['ref']}].")


async def browser_press(args: dict[str, Any], ctx: ToolContext) -> str:
    page = await ctx.runtime.browser.page()
    try:
        await page.keyboard.press(args["key"])
    except Exception as exc:
        raise ToolError(f"Unknown key '{args['key']}'. Examples: Enter, Escape, Tab") from exc
    return await _after_action(ctx, f"Pressed {args['key']}.")


async def browser_scroll(args: dict[str, Any], ctx: ToolContext) -> str:
    page = await ctx.runtime.browser.page()
    pixels = 700 if args.get("direction", "down") == "down" else -700
    await page.mouse.wheel(0, pixels * int(args.get("pages", 1)))
    await asyncio.sleep(0.4)
    return render_snapshot(await ctx.runtime.browser.snapshot())


async def browser_back(args: dict[str, Any], ctx: ToolContext) -> str:
    page = await ctx.runtime.browser.page()
    await page.go_back(timeout=15_000)
    return await _after_action(ctx, "Went back.")


async def browser_screenshot(args: dict[str, Any], ctx: ToolContext) -> ToolOutput:
    page = await ctx.runtime.browser.page()
    png = await page.screenshot(full_page=bool(args.get("full_page")), type="png")
    return ToolOutput(
        f"Screenshot of {page.url}", [ImagePart(base64.b64encode(png).decode("ascii"))]
    )


def browser_tools() -> list[Tool]:
    ref = {"type": "integer", "minimum": 1}
    return [
        Tool(
            "browser_open",
            "Open a URL in the agent's browser and list the page's interactive elements.",
            schema({"url": {"type": "string", "maxLength": 2048}}, ["url"]),
            "network",
            browser_open,
            blocking=False,
            timeout=60,
        ),
        Tool(
            "browser_snapshot",
            "Re-read the current page: interactive elements with [ref] numbers plus text.",
            schema({"max_items": {"type": "integer", "minimum": 10, "maximum": 300}}),
            "network",
            browser_snapshot,
            blocking=False,
        ),
        Tool(
            "browser_click",
            "Click an element by its [ref] from the latest snapshot.",
            schema({"ref": ref}, ["ref"]),
            "browser",
            browser_click,
            blocking=False,
        ),
        Tool(
            "browser_type",
            "Fill a text field by [ref]; set submit=true to press Enter afterwards.",
            schema(
                {
                    "ref": ref,
                    "text": {"type": "string", "maxLength": 10_000},
                    "submit": {"type": "boolean"},
                },
                ["ref", "text"],
            ),  # fmt: skip
            "browser",
            browser_type,
            blocking=False,
        ),
        Tool(
            "browser_select",
            "Choose an option in a <select> dropdown by [ref] and option label or value.",
            schema({"ref": ref, "option": {"type": "string"}}, ["ref", "option"]),
            "browser",
            browser_select,
            blocking=False,
        ),
        Tool(
            "browser_press",
            "Press a key in the page, such as Enter, Escape, Tab, or ArrowDown.",
            schema({"key": {"type": "string", "maxLength": 40}}, ["key"]),
            "browser",
            browser_press,
            blocking=False,
        ),
        Tool(
            "browser_scroll",
            "Scroll the page up or down by screens.",
            schema(
                {
                    "direction": {"type": "string", "enum": ["up", "down"]},
                    "pages": {"type": "integer", "minimum": 1, "maximum": 10},
                }
            ),
            "network",
            browser_scroll,
            blocking=False,
        ),
        Tool(
            "browser_back",
            "Go back to the previous page.",
            schema({}),
            "network",
            browser_back,
            blocking=False,
        ),
        Tool(
            "browser_screenshot",
            "See the current page as an image.",
            schema({"full_page": {"type": "boolean"}}),
            "network",
            browser_screenshot,
            blocking=False,
            requires_vision=True,
        ),
    ]
