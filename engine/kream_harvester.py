import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

TARGETS = [
    {
        'id': 'padding',
        'url': 'https://kream.co.kr/products/250560?base_product_id=250560',
        'raw_output': 'assets/brands/gsshop/raw/gsshop_padding_raw.png',
    },
    {
        'id': 'knit',
        'url': 'https://kream.co.kr/products/715923?base_product_id=715923',
        'raw_output': 'assets/brands/gsshop/raw/gsshop_knit_raw.png',
    },
]


async def harvest():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for item in TARGETS:
            print(f'Navigating to {item["url"]}...')
            await page.goto(item['url'], wait_until='domcontentloaded')
            try:
                await page.wait_for_selector(
                    'img.product_img, .item_inner img, .carousel_item img',
                    timeout=8000,
                )
            except Exception:
                await page.wait_for_selector('img', timeout=8000)
                print(f'Page title: {await page.title()}')
            images = await page.eval_on_selector_all(
                'img',
                'imgs => imgs.map(i => i.src).filter(src => src.includes("kream") || src.includes("product"))',
            )
            if not images:
                raise RuntimeError(f'No product images found at {item["url"]}')

            target_url = images[1] if len(images) > 1 else images[0]
            print(f'Fetching image: {target_url}')

            response = await page.request.get(target_url)
            body = await response.body()
            Path(item['raw_output']).parent.mkdir(parents=True, exist_ok=True)
            with open(item['raw_output'], 'wb') as f:
                f.write(body)
            print(f'Saved: {item["raw_output"]}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(harvest())
