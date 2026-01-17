"""
Browser Executor

Executes browser automation actions using Playwright.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, Error
from core.config import get_config
from utils.logger import log


class BrowserExecutor:
    """Execute browser automation actions"""
    
    def __init__(self):
        config = get_config()
        self.headless = config.execution.browser.headless
        self.viewport_width = config.execution.browser.viewport_width
        self.viewport_height = config.execution.browser.viewport_height
        self.default_timeout = config.execution.browser.default_timeout
        self.wait_after_nav = config.execution.browser.wait_after_navigation
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        log.info("Browser executor initialized")
    
    async def initialize(self):
        """Initialize Playwright browser"""
        if self.browser is not None:
            return
        
        log.info("Launching browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless
        )
        self.page = await self.browser.new_page(
            viewport={
                "width": self.viewport_width,
                "height": self.viewport_height
            }
        )
        self.page.set_default_timeout(self.default_timeout)
        log.info("Browser ready")
    
    async def cleanup(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        log.info("Browser closed")
    
    async def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a browser action.
        
        Args:
            action: Action name
            args: Action arguments
            
        Returns:
            Execution result
        """
        await self.initialize()
        log.info(f"Executing browser action: {action}")
        
        try:
            if action == "browser_open":
                return await self._open(args)
            elif action == "browser_search":
                return await self._search(args)
            elif action == "browser_click":
                return await self._click(args)
            elif action == "browser_scroll":
                return await self._scroll(args)
            elif action == "browser_extract":
                return await self._extract(args)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
        
        except Error as e:
            log.error(f"Browser action failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _open(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Open URL"""
        url = args["url"]
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(self.wait_after_nav)
        
        log.info(f"Opened URL: {url}")
        return {"success": True, "url": url}
    
    async def _search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search on Google"""
        query = args["query"]
        search_url = f"https://www.google.com/search?q={query}"
        
        await self.page.goto(search_url, wait_until="domcontentloaded")
        await asyncio.sleep(self.wait_after_nav)
        
        log.info(f"Searched: {query}")
        return {"success": True, "query": query}
    
    async def _click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click element by selector or text"""
        selector = args["selector"]
        
        # Try as CSS selector first
        try:
            await self.page.click(selector, timeout=5000)
            log.info(f"Clicked selector: {selector}")
            return {"success": True, "selector": selector}
        except:
            pass
        
        # Try as text content
        try:
            await self.page.click(f"text={selector}", timeout=5000)
            log.info(f"Clicked text: {selector}")
            return {"success": True, "selector": selector}
        except Exception as e:
            log.error(f"Could not click: {selector}")
            return {"success": False, "error": str(e)}
    
    async def _scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll page"""
        amount = int(args["amount"])
        
        await self.page.evaluate(f"window.scrollBy(0, {amount})")
        await asyncio.sleep(0.5)
        
        log.info(f"Scrolled: {amount}px")
        return {"success": True, "amount": amount}
    
    async def _extract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract information from page"""
        goal = args["goal"]
        
        # Get page text content
        text_content = await self.page.evaluate("""
            () => {
                return document.body.innerText;
            }
        """)
        
        # Simple extraction: return first 2000 chars
        extracted = text_content[:2000]
        
        log.info(f"Extracted content for goal: {goal}")
        return {
            "success": True,
            "goal": goal,
            "content": extracted
        }
    
    async def get_dom_summary(self) -> str:
        """Get simplified DOM summary"""
        if not self.page:
            return "Browser not initialized"
        
        try:
            summary = await self.page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a'))
                        .slice(0, 20)
                        .map(a => a.innerText.trim())
                        .filter(t => t.length > 0);
                    
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
                        .slice(0, 10)
                        .map(h => h.innerText.trim());
                    
                    const buttons = Array.from(document.querySelectorAll('button'))
                        .slice(0, 10)
                        .map(b => b.innerText.trim());
                    
                    return {
                        url: window.location.href,
                        title: document.title,
                        headings,
                        links,
                        buttons
                    };
                }
            """)
            
            return str(summary)
        except Exception as e:
            log.error(f"DOM extraction failed: {e}")
            return "DOM extraction failed"
