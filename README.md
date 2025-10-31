# Just Type It

A CLI typing tutor with a slick TUI interface, inspired by TypeRacer.

## Features

- **TypeRacer-style interface**: Type below the lesson text with real-time color feedback
- **Color-coded feedback**: Green for correct characters, red background for errors
- **Error enforcement**: Must backspace to fix mistakes before continuing (like a real typing test!)
- **Live statistics**: See your WPM, accuracy, and elapsed time in real-time
- **Multi-line support**: Preserves formatting with visible line breaks (↵ symbol)
- **Flexible input**: Direct text input, files, or default text
- **Customizable lessons**: Repeat and shuffle words/lines to create varied practice sessions
- **Zero dependencies**: Built with Python's curses library

## Installation

Make sure you have [uv](https://github.com/astral-sh/uv) installed, then:

```bash
git clone <your-repo-url>
cd just-type-it
chmod +x just_type_it.py
```

That's it! The script uses `uv run` in the shebang, so uv will handle the virtual environment automatically.

## Usage

### Basic usage with direct text input

```bash
./just_type_it.py --input "The quick brown fox jumps over the lazy dog"
# Or use the short form:
./just_type_it.py -i "hello world"
```

### From a text file

```bash
./just_type_it.py --text mytext.txt
# Or use the short form:
./just_type_it.py -t quotes.txt
```

The program preserves formatting, including line breaks. When you need to press Enter, you'll see a `↵` symbol.

### Default text

If you don't provide any text, it will use a default lesson:

```bash
./just_type_it.py
```

### Repeat lesson text

Concatenate the lesson text N times:

```bash
./just_type_it.py -i "one two three" --repeats 2
# Lesson will be: "one two three one two three"
```

### Shuffle

Randomize order (words for single-line text, lines for multi-line text):

```bash
# Single-line: shuffles words
./just_type_it.py -i "one two three four five" --shuffle
# Lesson might be: "three one five two four"

# Multi-line: shuffles lines/paragraphs
./just_type_it.py -t myfile.txt --shuffle
```

### Combine options

```bash
./just_type_it.py -t myfile.txt -r 3 -s
# Loads from file, repeats 3 times, and shuffles the words
```

### Repeat after completion

After finishing a lesson, press **R** to repeat the same lesson, or any other key to exit.

## Command Line Options

- `-i TEXT`, `--input TEXT`: Text to practice (passed directly as argument)
- `-t FILE`, `--text FILE`: Load text from a file
- `-r N`, `--repeats N`: Repeat the lesson text N times (default: 1)
- `-s`, `--shuffle`: Shuffle words (single-line) or lines (multi-line) in the lesson
- `-h`, `--help`: Show help message

## Keyboard Controls

- **Type normally**: Match the lesson text character by character
- **Enter/Return**: Press when you see the `↵` symbol to match line breaks
- **Backspace**: Fix mistakes by going back
- **ESC**: Quit the session early
- **R** (on summary screen): Repeat the lesson
- **Ctrl+C**: Also quits

## How It Works

1. **Start typing**: As soon as you type the first character, the timer starts
2. **Color feedback**:
   - Correctly typed characters turn green
   - Current character shows with a red background when you make a mistake
   - Untyped text remains in the default color
   - Line breaks display as `↵` - press Enter to match them
   - **You must backspace to fix errors before advancing**
3. **Typing display**: The bottom shows your progress on the current word (including any mistakes)
4. **Statistics**: Real-time WPM, accuracy percentage, and elapsed time
5. **Completion**: When you finish, see a summary screen with final statistics
6. **Repeat**: Press R on the summary to practice the same lesson again

## Statistics

- **WPM (Words Per Minute)**: Calculated as characters typed ÷ 5 ÷ minutes elapsed
- **Accuracy**: Correct keystrokes ÷ total keystrokes × 100
- **Time**: Elapsed seconds since first keystroke

## Examples

### Try the sample lesson

```bash
./just_type_it.py -t sample_lesson.txt
```

### Practice with custom text

```bash
./just_type_it.py -i "The quick brown fox jumps over the lazy dog"
```

### Create a varied practice session

```bash
./just_type_it.py -t sample_lesson.txt -r 3 -s
```

### Quick drill with repeated phrases

```bash
./just_type_it.py -i "the quick brown fox" -r 10
```

## Tips

- Start with short texts to warm up
- Use `--repeats` to build muscle memory for specific words or phrases
- Use `--shuffle` to prevent memorizing the exact order
- Remember: you must backspace to fix mistakes - this builds accuracy!
- Press R after completing a lesson to repeat it and improve your speed

## License

MIT

## Contributing

Issues and pull requests welcome!
