#!/usr/bin/env -S uv run
"""
just-type-it: A CLI typing tutor with a slick TUI interface
"""

import argparse
import curses
import logging
import random
import sys
import time
from typing import Optional

# Set up debug logging
logging.basicConfig(
    filename='/tmp/just_type_it.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s'
)


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


def load_text(text_file: Optional[str], text_input: Optional[str]) -> str:
    """Load text from file, direct input, or use default"""
    if text_input:
        return text_input
    elif text_file:
        with open(text_file, 'r') as f:
            return f.read().rstrip()  # Remove trailing whitespace but preserve internal formatting
    else:
        # Default text if nothing provided
        return "The quick brown fox jumps over the lazy dog"


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


def draw_lesson_text(stdscr, lesson: str, position: int, has_error: bool, start_y: int):
    """Draw the lesson text with color coding"""
    max_y, max_x = stdscr.getmaxyx()

    # Draw the lesson text with colors
    x, y = 0, start_y
    for i, char in enumerate(lesson):
        if y >= max_y - 4:  # Leave room for status and input
            break

        # Display newlines as a visible symbol
        display_char = char
        if char == '\n':
            display_char = '↵'

        if i < position:
            # Already typed correctly - green
            stdscr.addstr(y, x, display_char, curses.color_pair(1))
        elif i == position and has_error:
            # Current position with error - red background
            stdscr.addstr(y, x, display_char, curses.color_pair(2))
        else:
            # Not yet typed - default color
            stdscr.addstr(y, x, display_char)

        # Handle newlines and line wrapping
        if char == '\n':
            x = 0
            y += 1
        else:
            x += 1
            if x >= max_x - 1:
                x = 0
                y += 1


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


def typing_tutor(stdscr, lesson: str):
    """Main typing tutor interface using curses"""
    logging.info(f"Starting typing_tutor with lesson: {lesson[:50]}...")

    # Initialize colors
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Correct
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)    # Error
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Stats

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
        stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)

        # Draw the lesson text
        has_error = len(typed_chars) > 0
        draw_lesson_text(stdscr, lesson, position, has_error, 2)

        # Get current word and what user has typed for it
        current_word, word_start = get_current_word(lesson, position)

        # Calculate how much of the current word we've typed correctly
        chars_typed_in_word = position - word_start
        correctly_typed = lesson[word_start:position]

        # Combine correctly typed chars with any errors
        display_text = correctly_typed + typed_chars

        # Replace newlines with visible symbol for display
        display_text = display_text.replace('\n', '↵')

        # Draw current word being typed
        status_y = max_y - 4
        stdscr.addstr(status_y, 0, "─" * (max_x - 1))
        stdscr.addstr(status_y + 1, 0, f"Typing: {display_text}", curses.color_pair(3))

        # Draw statistics
        if position > 0:
            elapsed = stats.get_elapsed_time()
            wpm = stats.get_wpm(position)
            accuracy = stats.get_accuracy()
            stats_text = f"Time: {elapsed:.1f}s | WPM: {wpm:.1f} | Accuracy: {accuracy:.1f}%"
        else:
            stats_text = "Start typing to begin..."

        stdscr.addstr(max_y - 2, 0, stats_text, curses.color_pair(3))
        stdscr.addstr(max_y - 1, 0, "ESC to quit", curses.A_DIM)

        stdscr.refresh()

        # Check if lesson is complete
        if position >= len(lesson):
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

        # Handle ESC key
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
                expected_char = lesson[position]
                is_correct = (expected_char == '\n')
                stats.record_keystroke(is_correct)

                if is_correct:
                    # Correct Enter - advance position
                    # Check if the current word had errors before moving to next line
                    if current_word_had_error and position > 0:
                        current_word, word_start = get_current_word(lesson, position - 1)
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
                expected_char = lesson[position]

                # Record the keystroke
                is_correct = (char == expected_char)
                stats.record_keystroke(is_correct)

                if is_correct:
                    # Correct character - advance position
                    # Check if we just completed a word (typed space or newline)
                    if char in (' ', '\n') and current_word_had_error and position > 0:
                        # Extract the word we just completed (the word before this space/newline)
                        current_word, word_start = get_current_word(lesson, position - 1)
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
        current_word, word_start = get_current_word(lesson, position - 1)
        if current_word and current_word.strip():
            stats.record_mistyped_word(current_word)
            logging.info(f"Recorded final mistyped word: '{current_word}'")

    logging.info(f"Exiting typing_tutor loop, position={position}, lesson_length={len(lesson)}")
    return stats


def show_summary(stdscr, stats: TypingStats, lesson_length: int) -> bool:
    """Show final statistics summary. Returns True if user wants to repeat."""
    logging.info("show_summary called")

    # Make sure getch() blocks and waits for input
    stdscr.keypad(True)
    stdscr.nodelay(0)
    curses.cbreak()
    curses.noecho()
    stdscr.timeout(-1)

    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    title = "=== SUMMARY ==="
    stdscr.addstr(2, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)

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
        stdscr.addstr(y, max(0, (max_x - len(line)) // 2), line)
        y += 1

    # Add mistyped words section (left-justified within a centered block)
    top_mistyped = stats.get_top_mistyped_words(10)
    if top_mistyped:
        title = "=== TOP MISTYPED WORDS ==="
        stdscr.addstr(y, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
        y += 1
        y += 1  # Extra space after header

        # Find the longest line to determine block width
        mistyped_lines = []
        for i, (word, count) in enumerate(top_mistyped, 1):
            plural = "error" if count == 1 else "errors"
            mistyped_lines.append(f"  {i}. {word} ({count} {plural})")

        max_line_length = max(len(line) for line in mistyped_lines)

        # Draw each line left-justified within the centered block
        block_start_x = max(0, (max_x - max_line_length) // 2)
        for line in mistyped_lines:
            stdscr.addstr(y, block_start_x, line)
            y += 1
        y += 1

    # Draw final prompt (centered)
    prompt = "Press R to repeat or any other key to exit..."
    stdscr.addstr(y, max(0, (max_x - len(prompt)) // 2), prompt)

    stdscr.refresh()
    logging.info("Waiting for key press to exit summary...")
    key = stdscr.getch()
    logging.info(f"Got key {key} in summary")

    # Check if user wants to repeat (r or R)
    return key in (ord('r'), ord('R'))


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
    logging.info(f"Args: input={args.input}, text={args.text}, repeats={args.repeats}, shuffle={args.shuffle}")

    # Load and generate lesson text
    text = load_text(args.text, args.input)
    logging.info(f"Loaded text: {text[:100]}...")

    lesson = generate_lesson(text, args.repeats, args.shuffle)
    logging.info(f"Generated lesson (length={len(lesson)}): {lesson[:100]}...")

    if not lesson:
        logging.error("No lesson text available")
        print("Error: No text to practice with", file=sys.stderr)
        sys.exit(1)

    # Run the typing tutor - loop if user wants to repeat
    repeat = True
    while repeat:
        try:
            logging.info("Calling curses.wrapper(typing_tutor)")
            stats = curses.wrapper(typing_tutor, lesson)
            logging.info(f"typing_tutor returned, stats: keystrokes={stats.total_keystrokes}")

            # Show summary
            if stats.total_keystrokes > 0:
                logging.info("Showing summary")
                repeat = curses.wrapper(show_summary, stats, len(lesson))
                logging.info(f"Repeat = {repeat}")
            else:
                # User quit without typing anything
                repeat = False
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt in main")
            repeat = False
        except Exception as e:
            logging.exception("Exception in main")
            raise


if __name__ == '__main__':
    main()
