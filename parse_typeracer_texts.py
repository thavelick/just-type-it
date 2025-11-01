#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "beautifulsoup4",
# ]
# ///

"""
Parse TypeRacer texts from downloaded HTML and save each text to texts/<ID>.txt
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup


def parse_and_save_texts(html_file: str, output_dir: str = "texts"):
    """Parse TypeRacer texts HTML and save each text to a separate file."""

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Read the HTML file
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all text links in the table
    text_links = soup.find_all('a', href=re.compile(r'/text\?id=\d+'))

    print(f"Found {len(text_links)} texts")

    # Extract and save each text
    saved_count = 0
    for link in text_links:
        # Extract ID from href
        href = link['href']
        match = re.search(r'id=(\d+)', href)
        if not match:
            continue

        text_id = match.group(1)
        text_content = link.get_text()

        # Save to file
        output_path = Path(output_dir) / f"{text_id}.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)

        saved_count += 1
        if saved_count % 100 == 0:
            print(f"Saved {saved_count} texts...")

    print(f"\nSuccessfully saved {saved_count} texts to {output_dir}/")


if __name__ == "__main__":
    parse_and_save_texts("typeracer_texts.html")
