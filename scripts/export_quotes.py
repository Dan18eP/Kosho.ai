import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import extract_phrases


async def main():
    phrases = await extract_phrases()
    out = Path(__file__).resolve().parent.parent / "data" / "quotes.json"
    out.write_text(json.dumps(phrases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(phrases)} phrases to {out}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
