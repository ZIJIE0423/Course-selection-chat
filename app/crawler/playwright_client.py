from playwright.async_api import async_playwright

async def fetch_page(url: str, timeout: int = 30000) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=timeout, wait_until="networkidle")
            content = await page.content()
            return content
        except Exception as e:
            print(f"[playwright_client] 抓取 {url} 失败: {e}")
            return None
        finally:
            await browser.close()
