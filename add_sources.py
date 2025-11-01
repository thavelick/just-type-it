#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "beautifulsoup4",
# ]
# ///

"""
Add source attributions to TypeRacer texts by fetching from typeracerdata.com
"""

import argparse
import time
from pathlib import Path
from urllib.request import urlopen
from bs4 import BeautifulSoup


def has_preamble(file_path: Path) -> bool:
    """Check if a text file already has a preamble (contains '---' on its own line)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        return '\n---\n' in content


def get_text_id_from_filename(file_path: Path) -> str:
    """Extract the text ID from the filename (e.g., '3551496.txt' -> '3551496')"""
    return file_path.stem


def fetch_source_from_url(text_id: str) -> tuple[str | None, float]:
    """
    Fetch the source attribution from typeracerdata.com
    Returns (source, request_time_seconds)
    Raises exception on HTTP errors (will stop the script)
    """
    url = f"https://typeracerdata.com/text?id={text_id}"

    start_time = time.time()
    with urlopen(url) as response:
        # Use 'replace' to handle invalid UTF-8 bytes gracefully
        html = response.read().decode('utf-8', errors='replace')
    request_time = time.time() - start_time

    soup = BeautifulSoup(html, 'html.parser')

    # The source is in a <p> tag that contains "—from" or starts with "from"
    # Example: <p>&mdash;from <em>Whisper of the Heart</em>, a movie by Yoshifumi Kondō</p>
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        # Check if this looks like a source attribution
        if text.startswith('—from') or text.startswith('from'):
            # Remove the "—from" or "from" prefix and clean up
            source = text.replace('—from', '').replace('from', '', 1).strip()
            if source:
                return (source, request_time)

    # If we can't find it, return None
    return (None, request_time)


def update_file_with_preamble(file_path: Path, source: str):
    """Update a text file to include the source preamble"""
    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        original_text = f.read().rstrip()

    # Write new content with preamble
    new_content = f"source: {source}\n---\n{original_text}"

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def main():
    parser = argparse.ArgumentParser(
        description="Add source attributions to TypeRacer texts"
    )
    parser.add_argument(
        'count',
        type=int,
        help='Number of texts to process'
    )
    parser.add_argument(
        '--directory',
        default='texts',
        help='Directory containing text files (default: texts)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=3.0,
        help='Delay between requests in seconds (default: 3.0)'
    )

    args = parser.parse_args()

    texts_dir = Path(args.directory)
    if not texts_dir.exists():
        print(f"Error: Directory '{args.directory}' does not exist")
        return 1

    # Find all text files without preambles
    print(f"Scanning {args.directory}/ for texts without preambles...")
    files_without_preamble = []

    for file_path in sorted(texts_dir.glob('*.txt')):
        if not has_preamble(file_path):
            files_without_preamble.append(file_path)

    print(f"Found {len(files_without_preamble)} texts without preambles")

    if len(files_without_preamble) == 0:
        print("No texts to process!")
        return 0

    # Process up to the requested count
    to_process = files_without_preamble[:args.count]
    print(f"Processing {len(to_process)} texts with {args.delay}s delay between requests\n")

    successful = 0
    failed = 0

    try:
        for i, file_path in enumerate(to_process, 1):
            text_id = get_text_id_from_filename(file_path)
            print(f"[{i}/{len(to_process)}] Processing {file_path.name} (ID: {text_id})...", end=' ')

            source, request_time = fetch_source_from_url(text_id)

            if source:
                update_file_with_preamble(file_path, source)
                print(f"✓ Added source ({request_time:.2f}s): {source}")
                successful += 1
            else:
                print(f"✗ Could not find source ({request_time:.2f}s)")
                failed += 1

            # If request took more than 10 seconds, sleep for 30 seconds to let server recover
            if request_time > 10.0:
                print(f"  ⚠️  Slow response detected, sleeping 30s to let server recover...")
                time.sleep(30)
            # Sleep between requests (except after the last one)
            elif i < len(to_process):
                time.sleep(args.delay)

        print(f"\nComplete! Successful: {successful}, Failed: {failed}")
        return 0

    except KeyboardInterrupt:
        print(f"\n\nInterrupted by user. Processed {successful + failed} texts.")
        print(f"Successful: {successful}, Failed: {failed}")
        return 1
    except Exception as e:
        print(f"\n\nERROR: {e}")
        print(f"Stopped after processing {successful + failed} texts.")
        print(f"Successful: {successful}, Failed: {failed}")
        print(f"You can restart and it will skip already processed files.")
        raise


if __name__ == "__main__":
    exit(main())
