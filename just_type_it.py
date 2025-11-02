#!/usr/bin/env python3
"""
just-type-it: A CLI typing tutor with a slick TUI interface
"""

import argparse
import curses
import logging
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Set up debug logging
logging.basicConfig(
    filename='/tmp/just_type_it.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s'
)


@dataclass
class Lesson:
    """Represents a typing lesson with optional source attribution"""
    text: str
    source: Optional[str] = None


class DisplayLayout:
    """Manages display layout with margins and content width constraints"""

    MIN_TERMINAL_WIDTH = 40  # Minimum viable terminal width
    MAX_CONTENT_WIDTH = 100  # Maximum content width for readability
    MARGIN_PADDING = 4       # Minimum padding on sides

    def __init__(self, terminal_width: int):
        """Initialize layout for given terminal width"""
        self.terminal_width = terminal_width

        # Calculate content width: never exceed terminal, cap at MAX_CONTENT_WIDTH
        self.content_width = min(terminal_width - self.MARGIN_PADDING, self.MAX_CONTENT_WIDTH)

        # Calculate left margin for centering
        self.left_margin = max(0, (terminal_width - self.content_width) // 2)

    def center_x(self, text_length: int) -> int:
        """Calculate x position to center text within terminal"""
        return max(0, (self.terminal_width - text_length) // 2)

    def content_x(self, offset: int = 0) -> int:
        """Calculate x position within content area (with optional offset)"""
        return self.left_margin + offset

    @classmethod
    def check_terminal_size(cls, terminal_width: int) -> bool:
        """Check if terminal is large enough. Returns True if ok, False if too small."""
        return terminal_width >= cls.MIN_TERMINAL_WIDTH


class TextWrapper:
    """
    Wraps text at word boundaries and maintains position mapping.

    Maps between:
    - Original string index (what the user types through)
    - Wrapped display position (row, col for rendering)
    """

    def __init__(self, text: str, width: int):
        """
        Initialize wrapper for given text and width.

        Args:
            text: The original text to wrap
            width: Maximum line width for wrapping
        """
        self.text = text
        self.width = width
        self.wrapped_lines: list[str] = []
        self.index_to_pos: dict[int, tuple[int, int]] = {}  # original_index -> (row, col)

        self._wrap_text()

    def _wrap_text(self):
        """Wrap text at word boundaries and build position mapping"""
        current_line = ""
        current_row = 0
        current_col = 0
        original_idx = 0

        # Split by newlines first to preserve paragraph structure
        paragraphs = self.text.split('\n')

        for para_idx, paragraph in enumerate(paragraphs):
            if para_idx > 0:
                # Record the newline character position
                self.index_to_pos[original_idx] = (current_row, current_col)
                original_idx += 1

                # Move to next line for the newline
                if current_line:
                    self.wrapped_lines.append(current_line)
                    current_row += 1
                    current_line = ""
                    current_col = 0
                else:
                    # Empty line (consecutive newlines)
                    self.wrapped_lines.append("")
                    current_row += 1
                    current_col = 0

            # Process words in the paragraph
            words = paragraph.split(' ')
            for word_idx, word in enumerate(words):
                if word_idx > 0:
                    # Record the space position
                    self.index_to_pos[original_idx] = (current_row, current_col)
                    original_idx += 1

                # Check if word fits on current line
                word_len = len(word)
                space_needed = word_len if not current_line else len(current_line) + 1 + word_len

                if space_needed <= self.width:
                    # Word fits on current line
                    if current_line:
                        current_line += ' '
                        current_col += 1

                    # Add each character of the word with its position
                    for char in word:
                        self.index_to_pos[original_idx] = (current_row, current_col)
                        current_line += char
                        current_col += 1
                        original_idx += 1
                else:
                    # Word doesn't fit - need to wrap
                    if current_line:
                        # Finish current line and start new one
                        self.wrapped_lines.append(current_line)
                        current_row += 1
                        current_line = ""
                        current_col = 0

                    # Handle very long words that exceed line width
                    if word_len > self.width:
                        # Hard break the word
                        for char in word:
                            if current_col >= self.width:
                                self.wrapped_lines.append(current_line)
                                current_row += 1
                                current_line = ""
                                current_col = 0

                            self.index_to_pos[original_idx] = (current_row, current_col)
                            current_line += char
                            current_col += 1
                            original_idx += 1
                    else:
                        # Word fits on a new line
                        for char in word:
                            self.index_to_pos[original_idx] = (current_row, current_col)
                            current_line += char
                            current_col += 1
                            original_idx += 1

            # After processing all words in paragraph, if there's remaining text, save it
            # (but don't add a new line yet - wait for the next paragraph's newline)

        # Add any remaining text
        if current_line:
            self.wrapped_lines.append(current_line)

    def get_position(self, original_index: int) -> tuple[int, int]:
        """
        Get wrapped (row, col) position for an original string index.

        Returns:
            (row, col) tuple for rendering position
        """
        return self.index_to_pos.get(original_index, (0, 0))

    def get_line_count(self) -> int:
        """Get total number of wrapped lines"""
        return len(self.wrapped_lines)


class TypingStats:
    """Track typing statistics like WPM and accuracy"""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.correct_keystrokes = 0
        self.total_keystrokes = 0
        self.mistyped_words: dict[str, int] = {}  # word -> error count

    def start(self):
        """Start the timer"""
        self.start_time = time.time()

    def record_keystroke(self, correct: bool):
        """Record a keystroke"""
        self.total_keystrokes += 1
        if correct:
            self.correct_keystrokes += 1

    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def get_wpm(self, chars_typed: int) -> float:
        """Calculate words per minute (1 word = 5 characters)"""
        elapsed = self.get_elapsed_time()
        if elapsed == 0:
            return 0.0
        minutes = elapsed / 60
        words = chars_typed / 5
        return words / minutes if minutes > 0 else 0.0

    def get_accuracy(self) -> float:
        """Get accuracy percentage"""
        if self.total_keystrokes == 0:
            return 100.0
        return (self.correct_keystrokes / self.total_keystrokes) * 100

    def record_mistyped_word(self, word: str):
        """Record a word that was mistyped"""
        if word in self.mistyped_words:
            self.mistyped_words[word] += 1
        else:
            self.mistyped_words[word] = 1

    def get_top_mistyped_words(self, n: int = 10) -> list[tuple[str, int]]:
        """Get top N most mistyped words, sorted by error count descending"""
        sorted_words = sorted(self.mistyped_words.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:n]


def parse_preamble(text: str) -> tuple[str, Optional[str]]:
    """
    Parse optional preamble from text.

    Format:
        source: Movie Title
        ---
        Actual text to type

    Returns:
        (text_to_type, source) where source is None if no preamble found
    """
    lines = text.split('\n', 2)  # Split into at most 3 parts

    # Check if we have a preamble format: "source: ..." followed by "---"
    if len(lines) >= 3 and lines[0].startswith('source:') and lines[1].strip() == '---':
        source = lines[0][7:].strip()  # Remove "source:" prefix
        actual_text = lines[2]  # Everything after the ---
        return (actual_text, source)

    # No preamble found
    return (text, None)


def get_random_file_from_library(library_path: str) -> str:
    """Get a random file from a library directory"""
    library = Path(library_path)

    if not library.exists():
        raise FileNotFoundError(f"Library directory not found: {library_path}")

    if not library.is_dir():
        raise NotADirectoryError(f"Library path is not a directory: {library_path}")

    # Get all files in the directory (not subdirectories)
    files = [f for f in library.iterdir() if f.is_file()]

    if not files:
        raise ValueError(f"No files found in library directory: {library_path}")

    # Pick a random file
    random_file = random.choice(files)
    return str(random_file)


def load_text(text_file: Optional[str], text_input: Optional[str], library_path: Optional[str]) -> Lesson:
    """
    Load text from file, direct input, library, or use default.
    Returns a Lesson object with optional source attribution.
    """
    raw_text = None
    if text_input:
        raw_text = text_input
    elif library_path:
        # Pick a random file from the library
        random_file = get_random_file_from_library(library_path)
        logging.info(f"Selected random file from library: {random_file}")
        with open(random_file, 'r') as f:
            raw_text = f.read().rstrip()
    elif text_file:
        with open(text_file, 'r') as f:
            raw_text = f.read().rstrip()  # Remove trailing whitespace but preserve internal formatting
    else:
        # Default text if nothing provided
        raw_text = "The quick brown fox jumps over the lazy dog"

    # Parse preamble if present and return Lesson
    text, source = parse_preamble(raw_text)
    return Lesson(text=text, source=source)


def generate_lesson(text: str, repeats: int, shuffle: bool) -> str:
    """Generate the lesson text with repeats and optional shuffling"""
    # Check if text has newlines (multi-line)
    has_newlines = '\n' in text

    if has_newlines:
        # For multi-line text, split by lines and shuffle lines if requested
        lines = text.split('\n')

        # Repeat the lines
        if repeats > 1:
            lines = lines * repeats

        # Shuffle lines if requested
        if shuffle:
            random.shuffle(lines)

        return '\n'.join(lines)
    else:
        # For single-line text, shuffle words as before
        words = text.split()

        # Repeat the words list
        if repeats > 1:
            words = words * repeats

        # Shuffle if requested
        if shuffle:
            random.shuffle(words)

        # Join back into a single string
        return ' '.join(words)


def create_bag_shuffle_lesson(words: list[str], num_bags: int = 3) -> str:
    """
    Create a lesson using bag shuffle pattern (like modern Tetris).
    Each bag contains all words once, shuffled independently.

    Example: words=["a", "b"], num_bags=3
    Result: shuffle(["a","b"]) + shuffle(["a","b"]) + shuffle(["a","b"])
    Possible: "b a a b b a" but NOT "a a a b b b"
    """
    bags = []
    for _ in range(num_bags):
        bag = words.copy()
        random.shuffle(bag)
        bags.extend(bag)
    return ' '.join(bags)


def draw_lesson_text(stdscr, lesson: str, position: int, error_count: int, start_y: int, layout: DisplayLayout, source: Optional[str] = None):
    """Draw the lesson text with color coding and optional source"""
    max_y, max_x = stdscr.getmaxyx()

    # Create text wrapper for proper word wrapping
    wrapper = TextWrapper(lesson, layout.content_width)

    # Draw each character with appropriate color
    for i, char in enumerate(lesson):
        # Get wrapped position for this character
        row, col = wrapper.get_position(i)
        screen_y = start_y + row
        screen_x = layout.left_margin + col

        # Check if we've run out of vertical space
        if screen_y >= max_y - 4:
            break

        # Display newlines as a visible symbol
        display_char = char
        if char == '\n':
            display_char = '↵'

        # Determine color based on typing progress
        if i < position:
            # Already typed correctly - green
            stdscr.addstr(screen_y, screen_x, display_char, curses.color_pair(1))
        elif error_count > 0 and position <= i < position + error_count:
            # Current position through error buffer - red background
            stdscr.addstr(screen_y, screen_x, display_char, curses.color_pair(2))
        else:
            # Not yet typed - default color
            stdscr.addstr(screen_y, screen_x, display_char)

    # Draw source if present (after the lesson text)
    if source:
        # Position source below the wrapped text
        source_y = start_y + wrapper.get_line_count() + 1  # +1 for blank line spacing

        if source_y < max_y - 4:  # Make sure we have room
            source_text = f"— {source}"
            stdscr.addstr(source_y, layout.left_margin, source_text, curses.color_pair(4) | curses.A_DIM)


def get_current_word(lesson: str, position: int) -> tuple[str, int]:
    """Get the current word being typed and its start position"""
    # Find the start of the current word (stop at space or newline)
    word_start = position
    while word_start > 0 and lesson[word_start - 1] not in (' ', '\n'):
        word_start -= 1

    # Find the end of the current word (stop at space or newline)
    word_end = position
    while word_end < len(lesson) and lesson[word_end] not in (' ', '\n'):
        word_end += 1

    return lesson[word_start:word_end], word_start


def typing_tutor(stdscr, lesson: Lesson):
    """Main typing tutor interface using curses"""
    logging.info(f"Starting typing_tutor with lesson: {lesson.text[:50]}...")

    # Check terminal size
    max_y, max_x = stdscr.getmaxyx()
    if not DisplayLayout.check_terminal_size(max_x):
        stdscr.addstr(0, 0, f"Terminal too small! Need at least {DisplayLayout.MIN_TERMINAL_WIDTH} columns.")
        stdscr.addstr(1, 0, f"Current: {max_x} columns")
        stdscr.addstr(2, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        return TypingStats()  # Return empty stats

    # Create layout manager
    layout = DisplayLayout(max_x)

    # Initialize colors
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Correct
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)    # Error
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Stats
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Source

    # Hide cursor
    curses.curs_set(0)

    # Enable keypad mode for special keys
    stdscr.keypad(True)

    # Make sure getch() blocks and waits for input - try multiple approaches
    stdscr.nodelay(0)  # Try with int instead of bool
    curses.cbreak()    # Enable character break mode
    curses.noecho()    # Don't echo input
    stdscr.timeout(-1)  # Wait indefinitely for input

    logging.info(f"Set keypad, nodelay(0), cbreak, noecho, timeout(-1)")

    # Initialize stats
    stats = TypingStats()
    position = 0  # Position in the lesson text
    typed_chars = ""  # Characters typed for the current word (including errors)
    current_word_had_error = False  # Track if current word has any errors

    logging.info("Entering main loop")
    while True:
        stdscr.erase()  # Use erase() instead of clear() to reduce flicker
        max_y, max_x = stdscr.getmaxyx()

        # Draw title
        title = "=== JUST TYPE IT ==="
        stdscr.addstr(0, layout.center_x(len(title)), title, curses.A_BOLD)

        # Draw the lesson text
        error_count = len(typed_chars)
        draw_lesson_text(stdscr, lesson.text, position, error_count, 2, layout, lesson.source)

        # Get current word and what user has typed for it
        current_word, word_start = get_current_word(lesson.text, position)

        # Calculate how much of the current word we've typed correctly
        chars_typed_in_word = position - word_start
        correctly_typed = lesson.text[word_start:position]

        # Combine correctly typed chars with any errors
        display_text = correctly_typed + typed_chars

        # Replace newlines with visible symbol for display
        display_text = display_text.replace('\n', '↵')

        # Draw current word being typed
        status_y = max_y - 4
        # Draw separator line within content area
        stdscr.addstr(status_y, layout.left_margin, "─" * layout.content_width)
        stdscr.addstr(status_y + 1, layout.left_margin, f"Typing: {display_text}", curses.color_pair(3))

        # Draw statistics
        if position > 0:
            elapsed = stats.get_elapsed_time()
            wpm = stats.get_wpm(position)
            accuracy = stats.get_accuracy()
            stats_text = f"Time: {elapsed:.1f}s | WPM: {wpm:.1f} | Accuracy: {accuracy:.1f}%"
        else:
            stats_text = "Start typing to begin..."

        stdscr.addstr(max_y - 2, layout.left_margin, stats_text, curses.color_pair(3))
        stdscr.addstr(max_y - 1, layout.left_margin, "ESC to quit", curses.A_DIM)

        stdscr.refresh()

        # Check if lesson is complete
        if position >= len(lesson.text):
            break

        # Get user input
        try:
            key = stdscr.getch()
            # Log all keys for debugging
            logging.info(f"Got key: {key} ({repr(chr(key)) if 32 <= key <= 126 else 'non-printable'})")
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received")
            break
        except Exception as e:
            logging.exception(f"Exception during getch: {e}")
            break

        # Skip if no key available (shouldn't happen with blocking mode)
        if key == -1:
            logging.warning("Got -1 from getch (no input) - this shouldn't happen in blocking mode!")
            continue

        # Start timer on first keystroke
        if stats.start_time is None:
            stats.start()
            logging.info("Timer started")

        # Handle ESC key to quit
        if key == 27:  # ESC
            logging.info("ESC pressed, exiting")
            break

        # Handle backspace
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            logging.info(f"Backspace: position={position}, typed_chars='{typed_chars}'")
            if len(typed_chars) > 0:
                # Remove from typed chars buffer
                typed_chars = typed_chars[:-1]
            elif position > 0:
                # If no errors, go back to previous character
                position -= 1
                typed_chars = ""

        # Handle Enter/Return key
        elif key in (10, 13, curses.KEY_ENTER):
            # If there are errors, don't allow advancing
            if typed_chars:
                stats.record_keystroke(False)
                typed_chars += '↵'
                logging.info(f"Blocked Enter (must fix errors first) -> typed_chars='{typed_chars}'")
            else:
                expected_char = lesson.text[position]
                is_correct = (expected_char == '\n')
                stats.record_keystroke(is_correct)

                if is_correct:
                    # Correct Enter - advance position
                    # Check if the current word had errors before moving to next line
                    if current_word_had_error and position > 0:
                        current_word, word_start = get_current_word(lesson.text, position - 1)
                        if current_word and current_word.strip():  # Ensure it's not empty or whitespace
                            stats.record_mistyped_word(current_word)
                            logging.info(f"Recorded mistyped word: '{current_word}'")
                        current_word_had_error = False  # Reset for next word

                    position += 1
                    typed_chars = ""
                    logging.info(f"Correct Enter -> position={position}")
                else:
                    # Wrong - trying to press Enter when we shouldn't
                    typed_chars += '↵'
                    current_word_had_error = True  # Mark current word as having errors
                    logging.info(f"Wrong Enter (expected '{repr(expected_char)}') -> typed_chars='{typed_chars}'")

        # Handle printable characters
        elif 32 <= key <= 126:
            char = chr(key)

            # If there are errors, don't allow advancing - only add to error buffer
            if typed_chars:
                stats.record_keystroke(False)
                typed_chars += char
                current_word_had_error = True  # Mark current word as having errors
                logging.info(f"Blocked '{char}' (must fix errors first) -> typed_chars='{typed_chars}'")
            else:
                expected_char = lesson.text[position]

                # Record the keystroke
                is_correct = (char == expected_char)
                stats.record_keystroke(is_correct)

                if is_correct:
                    # Correct character - advance position
                    # Check if we just completed a word (typed space or newline)
                    if char in (' ', '\n') and current_word_had_error and position > 0:
                        # Extract the word we just completed (the word before this space/newline)
                        current_word, word_start = get_current_word(lesson.text, position - 1)
                        if current_word and current_word.strip():  # Ensure it's not empty or whitespace
                            stats.record_mistyped_word(current_word)
                            logging.info(f"Recorded mistyped word: '{current_word}'")
                        current_word_had_error = False  # Reset for next word

                    position += 1
                    typed_chars = ""
                    logging.info(f"Correct '{char}' -> position={position}")
                else:
                    # Wrong character - add to typed chars to show error
                    typed_chars += char
                    current_word_had_error = True  # Mark current word as having errors
                    logging.info(f"Wrong '{char}' (expected '{expected_char}') -> typed_chars='{typed_chars}'")

    # Handle the last word if it had errors and wasn't followed by space/newline
    if current_word_had_error and position > 0:
        current_word, word_start = get_current_word(lesson.text, position - 1)
        if current_word and current_word.strip():
            stats.record_mistyped_word(current_word)
            logging.info(f"Recorded final mistyped word: '{current_word}'")

    logging.info(f"Exiting typing_tutor loop, position={position}, lesson_length={len(lesson.text)}")
    return stats


def show_summary(stdscr, stats: TypingStats, lesson_length: int, can_go_back: bool, in_library_mode: bool = False) -> str:
    """
    Show final statistics summary.
    Returns action: "repeat", "mistakes", "back", "new", or "quit"
    """
    logging.info("show_summary called")

    # Make sure getch() blocks and waits for input
    stdscr.keypad(True)
    stdscr.nodelay(0)
    curses.cbreak()
    curses.noecho()
    stdscr.timeout(-1)

    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    # Create layout manager
    layout = DisplayLayout(max_x)

    title = "=== SUMMARY ==="
    stdscr.addstr(2, layout.center_x(len(title)), title, curses.A_BOLD)

    elapsed = stats.get_elapsed_time()
    wpm = stats.get_wpm(lesson_length)
    accuracy = stats.get_accuracy()

    # Build main stats lines (these will be centered)
    centered_lines = [
        "",
        f"Time: {elapsed:.2f} seconds",
        f"WPM: {wpm:.2f}",
        f"Accuracy: {accuracy:.2f}%",
        f"Correct keystrokes: {stats.correct_keystrokes}",
        f"Total keystrokes: {stats.total_keystrokes}",
        ""
    ]

    # Draw centered stats
    start_y = 4
    y = start_y
    for line in centered_lines:
        stdscr.addstr(y, layout.center_x(len(line)), line)
        y += 1

    # Add mistyped words section (left-justified within a centered block)
    top_mistyped = stats.get_top_mistyped_words(10)
    if top_mistyped:
        title = "=== TOP MISTYPED WORDS ==="
        stdscr.addstr(y, layout.center_x(len(title)), title, curses.A_BOLD)
        y += 1
        y += 1  # Extra space after header

        # Find the longest line to determine block width
        mistyped_lines = []
        for i, (word, count) in enumerate(top_mistyped, 1):
            plural = "error" if count == 1 else "errors"
            mistyped_lines.append(f"  {i}. {word} ({count} {plural})")

        max_line_length = max(len(line) for line in mistyped_lines)

        # Draw each line left-justified within the centered block
        block_start_x = layout.center_x(max_line_length)
        for line in mistyped_lines:
            stdscr.addstr(y, block_start_x, line)
            y += 1
        y += 1

    # Build prompt based on available options
    has_mistakes = len(stats.mistyped_words) > 0
    prompt_parts = ["R: repeat"]
    if has_mistakes:
        prompt_parts.append("M: practice mistakes")
    if in_library_mode:
        prompt_parts.append("N: new text")
    if can_go_back:
        prompt_parts.append("B: go back")
    prompt_parts.append("Q: quit")
    prompt = " | ".join(prompt_parts)

    # Draw final prompt (centered)
    stdscr.addstr(y, layout.center_x(len(prompt)), prompt)

    stdscr.refresh()

    # Loop until user presses a valid key
    while True:
        logging.info("Waiting for key press in summary...")
        key = stdscr.getch()
        logging.info(f"Got key {key} in summary")

        # Check which action was requested
        if key in (ord('r'), ord('R')):
            return "repeat"
        elif key in (ord('m'), ord('M')) and has_mistakes:
            return "mistakes"
        elif key in (ord('n'), ord('N')) and in_library_mode:
            return "new"
        elif key in (ord('b'), ord('B')) and can_go_back:
            return "back"
        elif key in (ord('q'), ord('Q')):
            return "quit"
        # If invalid key, loop continues (do nothing)


def main():
    """Main entry point"""
    logging.info("=== Starting just-type-it ===")

    parser = argparse.ArgumentParser(
        description="A CLI typing tutor with a slick TUI interface"
    )
    parser.add_argument(
        '-i', '--input',
        help='Text to use for typing practice (directly as argument)'
    )
    parser.add_argument(
        '-t', '--text',
        help='Text file to use for typing practice'
    )
    parser.add_argument(
        '-l', '--library',
        help='Path to directory containing text files - will select a random file'
    )
    parser.add_argument(
        '-r', '--repeats',
        type=int,
        default=1,
        help='Number of times to repeat the lesson text (default: 1)'
    )
    parser.add_argument(
        '-s', '--shuffle',
        action='store_true',
        help='Shuffle words in the lesson text'
    )

    args = parser.parse_args()
    logging.info(f"Args: input={args.input}, text={args.text}, library={args.library}, repeats={args.repeats}, shuffle={args.shuffle}")

    # Store library path for later use
    library_path = args.library
    in_library_mode = library_path is not None

    # Load and generate lesson text
    loaded = load_text(args.text, args.input, library_path)
    logging.info(f"Loaded text: {loaded.text[:100]}...")
    if loaded.source:
        logging.info(f"Source: {loaded.source}")

    lesson_text = generate_lesson(loaded.text, args.repeats, args.shuffle)
    logging.info(f"Generated lesson (length={len(lesson_text)}): {lesson_text[:100]}...")

    if not lesson_text:
        logging.error("No lesson text available")
        print("Error: No text to practice with", file=sys.stderr)
        sys.exit(1)

    # Create initial lesson with source
    initial_lesson = Lesson(text=lesson_text, source=loaded.source)

    # Run the typing tutor with lesson stack
    lesson_stack = [initial_lesson]  # Start with original lesson

    while True:
        try:
            # Get current lesson from top of stack
            current_lesson = lesson_stack[-1]
            logging.info(f"Current lesson (stack depth={len(lesson_stack)}): {current_lesson.text[:50]}...")

            # Run typing tutor
            logging.info("Calling curses.wrapper(typing_tutor)")
            stats = curses.wrapper(typing_tutor, current_lesson)
            logging.info(f"typing_tutor returned, stats: keystrokes={stats.total_keystrokes}")

            # Show summary if user typed anything
            if stats.total_keystrokes > 0:
                logging.info("Showing summary")
                can_go_back = len(lesson_stack) > 1
                action = curses.wrapper(show_summary, stats, len(current_lesson.text), can_go_back, in_library_mode)
                logging.info(f"Action = {action}")

                if action == "repeat":
                    # Repeat current lesson - just continue loop
                    continue
                elif action == "mistakes":
                    # Create new lesson from mistyped words
                    top_words = [word for word, _ in stats.get_top_mistyped_words(10)]
                    if top_words:
                        mistake_lesson_text = create_bag_shuffle_lesson(top_words, 3)
                        # Mistake lessons have no source
                        mistake_lesson = Lesson(text=mistake_lesson_text, source=None)
                        lesson_stack.append(mistake_lesson)
                        logging.info(f"Created mistake lesson: {mistake_lesson_text[:50]}...")
                elif action == "new":
                    # Load a new random text from library
                    loaded = load_text(None, None, library_path)
                    new_lesson_text = generate_lesson(loaded.text, args.repeats, args.shuffle)
                    # Add new lesson to stack with its source
                    new_lesson = Lesson(text=new_lesson_text, source=loaded.source)
                    lesson_stack.append(new_lesson)
                    logging.info(f"Created new lesson from library: {new_lesson_text[:50]}...")
                elif action == "back":
                    # Go back to previous lesson
                    if len(lesson_stack) > 1:
                        lesson_stack.pop()
                        logging.info(f"Went back, stack depth now: {len(lesson_stack)}")
                elif action == "quit":
                    # Exit program
                    break
            else:
                # User quit without typing anything
                break

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt in main")
            break
        except Exception as e:
            logging.exception("Exception in main")
            raise


if __name__ == '__main__':
    main()
