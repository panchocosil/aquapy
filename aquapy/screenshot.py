from __future__ import annotations
from typing import Optional
from PIL import Image
import imagehash, asyncio
from .models import ShotResult
from playwright.async_api import async_playwright

MOBILE_PROFILES = {
    "mobile": {
        "viewport": {"width": 390, "height": 844},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    },
    "desktop": {
        "viewport": {"width": 1440, "height": 900},
        "user_agent": "aquapy/0.5.0 (Chromium via Playwright)"
    }
}

async def _take(browser, url: str, out_path: str, viewport: dict, user_agent: str, timeout_ms: int, full_page: bool, proxy: Optional[str]) -> Optional[str]:
    context_kwargs = {"viewport": viewport, "user_agent": user_agent, "ignore_https_errors": True}
    if proxy:
        context_kwargs["proxy"] = {"server": proxy}
    ctx = await browser.new_context(**context_kwargs)
    page = await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    await page.evaluate("() => window.scrollTo(0, 0)")
    await page.screenshot(path=out_path, full_page=full_page)
    await ctx.close()
    return out_path

async def screenshot_url(url: str, out_path: str, width: int, height: int, user_agent: str, timeout_ms: int = 30000, proxy: Optional[str]=None, chrome_path: Optional[str]=None, full_page: bool=False, profile: str="desktop", retries: int=1) -> ShotResult:
    try:
        async with async_playwright() as p:
            launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
            if chrome_path:
                launch_kwargs["executable_path"] = chrome_path
            browser = await p.chromium.launch(**launch_kwargs)
            prof = MOBILE_PROFILES.get(profile, MOBILE_PROFILES["desktop"])
            vp = prof["viewport"] if profile in MOBILE_PROFILES else {"width": width, "height": height}
            ua = prof["user_agent"] if profile in MOBILE_PROFILES else user_agent

            last_exc = None
            for attempt in range(retries+1):
                try:
                    path = await _take(browser, url, out_path, vp, ua, timeout_ms, full_page, proxy)
                    ph = None
                    try:
                        img = Image.open(out_path)
                        ph = str(imagehash.phash(img))
                    except Exception:
                        pass
                    await browser.close()
                    return ShotResult(url=url, path=path, width=vp["width"], height=vp["height"], phash=ph, error=None)
                except Exception as e:
                    last_exc = e
                    if attempt < retries:
                        await asyncio.sleep(0.25 * (attempt+1))
                    else:
                        await browser.close()
                        raise last_exc
    except Exception as e:
        return ShotResult(url=url, path=None, width=width, height=height, phash=None, error=str(e))
