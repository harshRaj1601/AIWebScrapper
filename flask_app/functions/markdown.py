# markdown.py

import asyncio
from typing import List
from functions.api_management import get_database_session
from services.utils import generate_unique_name
from crawl4ai import AsyncWebCrawler
from services.database import ScrapedData


async def get_fit_markdown_async(url: str) -> str:
    """
    Async function using crawl4ai's AsyncWebCrawler to produce the regular raw markdown.
    (Reverting from the 'fit' approach back to normal.)
    """

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            return result.markdown
        else:
            return ""


def fetch_fit_markdown(url: str) -> str:
    """
    Synchronous wrapper around get_fit_markdown_async().
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_fit_markdown_async(url))
    finally:
        loop.close()

def read_raw_data(unique_name: str) -> str:
    """
    Query the 'scraped_data' table for the row with this unique_name,
    and return the 'raw_data' field.
    """
    db = get_database_session()
    try:
        result = db.query(ScrapedData).filter(ScrapedData.unique_name == unique_name).first()
        if result:
            return result.raw_data or ""
        return ""
    finally:
        db.close()

def save_raw_data(unique_name: str, url: str, raw_data: str) -> None:
    """
    Save or update the row in database with unique_name, url, and raw_data.
    If a row with unique_name doesn't exist, it inserts; otherwise it updates.
    """
    db = get_database_session()
    try:
        # Check if record exists
        existing = db.query(ScrapedData).filter(ScrapedData.unique_name == unique_name).first()
        
        if existing:
            # Update existing record
            existing.url = url
            existing.raw_data = raw_data
        else:
            # Create new record
            new_record = ScrapedData(unique_name=unique_name, url=url, raw_data=raw_data)
            db.add(new_record)
        
        db.commit()
        BLUE = "\033[34m"
        RESET = "\033[0m"
        print(f"{BLUE}INFO:Raw data stored for {unique_name}{RESET}")
    except Exception as e:
        db.rollback()
        print(f"Error saving raw data: {e}")
    finally:
        db.close()

def fetch_and_store_markdowns(urls: List[str]) -> List[str]:
    """
    For each URL:
      1) Generate unique_name
      2) Check if there's already a row in database with that unique_name
      3) If not found or if raw_data is empty, fetch fit_markdown
      4) Save to database
    Return a list of unique_names (one per URL).
    """
    unique_names = []

    for url in urls:
        unique_name = generate_unique_name(url)
        MAGENTA = "\033[35m"
        RESET = "\033[0m"
        # check if we already have raw_data in database
        raw_data = read_raw_data(unique_name)
        if raw_data:
            print(f"{MAGENTA}Found existing data in database for {url} => {unique_name}{RESET}")
        else:
            # fetch fit markdown
            fit_md = fetch_fit_markdown(url)
            print(fit_md)
            save_raw_data(unique_name, url, fit_md)
        unique_names.append(unique_name)

    return unique_names
