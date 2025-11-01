#!/usr/bin/env python3
"""
Fix "a other" sources by using LLM to suggest better phrasing
"""

import argparse
import json
import subprocess
import sys
import time
import tty
import termios
from pathlib import Path


PROGRESS_FILE = ".fix_progress.json"


def load_progress():
    """Load progress from JSON file"""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"processed": []}


def save_progress(progress):
    """Save progress to JSON file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def get_single_key():
    """Get a single keypress from the user without requiring Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        # Check for Ctrl+C (ASCII 3)
        if ord(ch) == 3:
            raise KeyboardInterrupt
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def get_llm_suggestion(source_text):
    """Get LLM suggestion for rewriting the source"""
    prompt = f"""Rewrite this source to avoid using "a other". Examples:

From: All in the Family, a other by Norman Lear
To: All in the Family, a TV show by Norman Lear

From: Hop Quote, a other by Submitted by Kendrick Lamar - www.brainyquote.com
To: a quote by Kendrick Lamar from www.brainyquote.com

From: Letter Birmingham Jail, a other by Martin Luther King Jr.
To: A Letter from Birmingham Jail, an essay by Martin Luther King Jr.

From: Short Joke, a other by boredpanda.com
To: a quote from boredpanda.com

Now rewrite: {source_text}

Respond with ONLY the rewritten source, nothing else."""

    try:
        result = subprocess.run(
            ['llm'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("  ⚠️  LLM timeout, skipping...")
        return None
    except Exception as e:
        print(f"  ⚠️  LLM error: {e}")
        return None


def find_files_with_source(source_line, texts_dir):
    """Find all text files containing this source line"""
    try:
        # Use grep to find files containing the exact source line
        # Need to use shell=True to properly expand the glob
        grep_pattern = f"{texts_dir}/*.txt"
        result = subprocess.run(
            f"grep -l -F {subprocess.list2cmdline([source_line])} {grep_pattern}",
            capture_output=True,
            text=True,
            shell=True
        )
        if result.returncode == 0:
            return [Path(f.strip()) for f in result.stdout.split('\n') if f.strip()]
        return []
    except Exception as e:
        print(f"  ⚠️  Error finding files: {e}")
        return []


def replace_in_file(file_path, old_line, new_line):
    """Replace old source line with new source line in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace the exact line
        new_content = content.replace(old_line, new_line)

        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"  ⚠️  Error updating {file_path}: {e}")
        return False


def replace_source_in_files(old_source, new_source, texts_dir):
    """Replace source in all matching files"""
    old_line = f"source: {old_source}"
    new_line = f"source: {new_source}"

    files = find_files_with_source(old_line, texts_dir)

    if not files:
        print(f"  ⚠️  No files found with this source")
        return 0

    updated = 0
    for file_path in files:
        if replace_in_file(file_path, old_line, new_line):
            updated += 1

    print(f"  ✓ Updated {updated} file(s)")
    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Fix 'a other' sources using LLM suggestions"
    )
    parser.add_argument(
        '--directory',
        default='texts',
        help='Directory containing text files (default: texts)'
    )
    parser.add_argument(
        '--sources-file',
        default='sources_with_other.txt',
        help='File containing sources to fix (default: sources_with_other.txt)'
    )
    parser.add_argument(
        '--yolo',
        action='store_true',
        help='Auto-accept all LLM suggestions without confirmation'
    )
    args = parser.parse_args()

    texts_dir = Path(args.directory)
    if not texts_dir.exists():
        print(f"Error: Directory '{args.directory}' not found")
        return 1

    # Load sources to fix
    sources_file = Path(args.sources_file)
    if not sources_file.exists():
        print(f"Error: {args.sources_file} not found")
        return 1

    with open(sources_file, 'r') as f:
        sources = [line.strip() for line in f if line.strip()]

    # Load progress
    progress = load_progress()
    processed_set = set(progress["processed"])

    # Filter out already processed
    remaining = [s for s in sources if s not in processed_set]

    print(f"Directory: {texts_dir}")
    print(f"Total sources: {len(sources)}")
    print(f"Already processed: {len(processed_set)}")
    print(f"Remaining: {len(remaining)}\n")

    if not remaining:
        print("All sources already processed!")
        return 0

    try:
        for i, source_line in enumerate(remaining, 1):
            # Source line already has "source: " prefix from the file
            # Extract just the attribution text
            if source_line.startswith("source: "):
                source_text = source_line[8:]  # Remove "source: " prefix
            else:
                source_text = source_line

            print(f"[{i}/{len(remaining)}] Processing:")
            print(f"  Original: {source_text}")

            # Get LLM suggestion
            suggestion = get_llm_suggestion(source_text)

            if suggestion is None:
                # Skip if LLM failed
                progress["processed"].append(source_line)
                save_progress(progress)
                continue

            print(f"  Suggested: {suggestion}")

            # Auto-accept in yolo mode
            if args.yolo:
                print("  [YOLO mode: auto-accepting]")
                replace_source_in_files(source_text, suggestion, texts_dir)
            else:
                # Ask user
                while True:
                    print("  Accept? (y/n/s, Enter=yes): ", end='', flush=True)
                    response = get_single_key().lower()

                    # Handle newline/return as 'y'
                    if response in ('\n', '\r'):
                        response = 'y'

                    # Echo the response
                    if response in ('y', 'n', 's'):
                        print(response)
                    else:
                        print(response)
                        print("  Invalid response. Use y/n/s")
                        continue

                    if response == 'y':
                        # Accept suggestion
                        replace_source_in_files(source_text, suggestion, texts_dir)
                        break
                    elif response == 'n':
                        # Ask for manual input (needs full line)
                        manual = input("  Enter replacement: ").strip()
                        if manual:
                            replace_source_in_files(source_text, manual, texts_dir)
                        break
                    elif response == 's':
                        # Skip
                        print("  ⊘ Skipped")
                        break

            # Mark as processed
            progress["processed"].append(source_line)
            save_progress(progress)
            print()

            # Sleep in yolo mode to avoid hammering the LLM
            if args.yolo:
                time.sleep(0.25)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress saved.")
        print(f"Processed {len(progress['processed'])} total sources.")
        print("Run again to continue from where you left off.")
        return 1

    print(f"\nComplete! Processed {len(progress['processed'])} sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
