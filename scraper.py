import asyncio
import sys
from playwright.async_api import async_playwright

async def extract_phrases():
    phrases = []
    page_number = 1
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False)
        page = await browser.new_page()
        
        quote_flag = True
        
        while quote_flag:
            print(f"Scraping page {page_number}...")
            await page.goto(f"https://quotes.toscrape.com/page/{page_number}/") 
            
            elements = await page.locator(".quote").all()
            
            if elements:
                for element in elements:
                    phrase = await element.locator(".text").inner_text()
                    phrase = phrase.replace('“', "").replace('”', "")
                    author = await element.locator(".author").inner_text()
                    
                    phrases.append({
                        "phrase": phrase,
                        "author": author
                    })
                page_number += 1
            else:
                quote_flag = False
                
        await browser.close()
            
    return phrases

async def main():
    phrases = await extract_phrases()
    print(f"Successfully scraped {len(phrases)} phrases:")
    for p in phrases[:5]:
        print(f"- {p['phrase']} (by {p['author']})")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
