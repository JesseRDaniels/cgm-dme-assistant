#!/usr/bin/env python3
"""
Scrape LCD documents from CMS for CGM coverage.

Main LCD: L33822 - Continuous Glucose Monitors (CGM)
"""
import httpx
import asyncio
import json
from pathlib import Path
from bs4 import BeautifulSoup
import html2text

# LCD URLs for CGM coverage
LCD_SOURCES = [
    {
        "id": "L33822",
        "name": "Continuous Glucose Monitors",
        "url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=33822",
        "jurisdiction": "National",
    },
    # Add more LCDs as needed
]

# HCPCS code reference page
HCPCS_URL = "https://www.cms.gov/medicare/payment/fee-schedules/durable-medical-equipment-prosthetics-orthotics-supplies"

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"


async def fetch_page(url: str) -> str:
    """Fetch a webpage."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        return response.text


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean markdown."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # No wrapping
    return h.handle(html)


def extract_lcd_content(html: str) -> dict:
    """Extract LCD sections from CMS page."""
    soup = BeautifulSoup(html, "html.parser")

    content = {
        "title": "",
        "sections": {},
        "full_text": "",
    }

    # Try to find the title
    title_elem = soup.find("h1") or soup.find("title")
    if title_elem:
        content["title"] = title_elem.get_text(strip=True)

    # Look for common LCD section headings
    section_headings = [
        "Coverage Indications, Limitations, and/or Medical Necessity",
        "Coverage Indications",
        "Limitations",
        "Medical Necessity",
        "Documentation Requirements",
        "Coding Guidelines",
        "Utilization Guidelines",
        "Summary of Evidence",
    ]

    # Extract main content area
    main_content = soup.find("main") or soup.find("div", {"class": "content"}) or soup.body

    if main_content:
        content["full_text"] = html_to_markdown(str(main_content))

        # Try to extract sections
        for heading in section_headings:
            section_elem = main_content.find(string=lambda t: t and heading.lower() in t.lower())
            if section_elem:
                # Get the next sibling content
                parent = section_elem.parent
                if parent:
                    next_content = []
                    for sibling in parent.find_next_siblings():
                        if sibling.name in ["h1", "h2", "h3"]:
                            break
                        next_content.append(sibling.get_text(strip=True))
                    if next_content:
                        content["sections"][heading] = "\n".join(next_content)

    return content


async def scrape_lcd(lcd_info: dict) -> dict:
    """Scrape a single LCD document."""
    print(f"Fetching LCD {lcd_info['id']}: {lcd_info['name']}...")

    try:
        html = await fetch_page(lcd_info["url"])
        content = extract_lcd_content(html)

        return {
            "id": lcd_info["id"],
            "name": lcd_info["name"],
            "jurisdiction": lcd_info["jurisdiction"],
            "url": lcd_info["url"],
            "content": content,
        }

    except Exception as e:
        print(f"Error fetching {lcd_info['id']}: {e}")
        return {
            "id": lcd_info["id"],
            "error": str(e),
        }


async def main():
    """Scrape all LCD documents."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Starting LCD scrape...")

    for lcd_info in LCD_SOURCES:
        result = await scrape_lcd(lcd_info)

        # Save to file
        output_file = OUTPUT_DIR / f"lcd_{lcd_info['id']}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"Saved: {output_file}")

    print("\nDone! Check data/raw/ for results.")
    print("\nNote: CMS pages may require manual download or API access.")
    print("Consider downloading PDFs directly from Medicare Coverage Database.")


if __name__ == "__main__":
    asyncio.run(main())
