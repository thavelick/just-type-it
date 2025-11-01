# Just Type It

A CLI typing tutor with a slick TUI interface, inspired by TypeRacer.

## Features

- **TypeRacer-style interface**: Type below the lesson text with real-time color feedback
- **Color-coded feedback**: Green for correct characters, red background for errors
- **Error enforcement**: Must backspace to fix mistakes before continuing (like a real typing test!)
- **Live statistics**: See your WPM, accuracy, and elapsed time in real-time
- **Mistyped word tracking**: See your top 10 most mistyped words after each session
- **Practice your mistakes**: Press M to create a new lesson from your mistyped words
- **Lesson stack**: Go back to previous lessons with B, supports nested mistake practice
- **Bag shuffle**: Mistake lessons use "bag shuffle" pattern (like Tetris) for optimal practice
- **Multi-line support**: Preserves formatting with visible line breaks (↵ symbol)
- **Flexible input**: Direct text input, files, random selection from a library directory, or default text
- **TypeRacer text library**: 11,871+ real TypeRacer texts available via the `--library` option
- **Customizable lessons**: Repeat and shuffle words/lines to create varied practice sessions
- **Zero dependencies**: Built with Python's curses library

## Installation

Make sure you have [uv](https://github.com/astral-sh/uv) installed, then:

```bash
git clone https://github.com/thavelick/just-type-it.git
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

### Random text from a library directory

```bash
./just_type_it.py --library texts
# Or use the short form:
./just_type_it.py -l texts
```

This will randomly select one file from the specified directory and use its content as the lesson text. Perfect for variety when you have a collection of texts!

**TypeRacer text library**: Download 11,871+ real TypeRacer texts using the included parser script:

```bash
# Download and parse TypeRacer texts (one-time setup)
curl -o typeracer_texts.html "https://typeracerdata.com/texts?texts=full&sort=relative_average"
uv run parse_typeracer_texts.py

# Now you can practice with random TypeRacer texts!
./just_type_it.py --library texts
```

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
- `-l DIR`, `--library DIR`: Randomly select a text file from the specified directory
- `-r N`, `--repeats N`: Repeat the lesson text N times (default: 1)
- `-s`, `--shuffle`: Shuffle words (single-line) or lines (multi-line) in the lesson
- `-h`, `--help`: Show help message

## Keyboard Controls

### During Typing
- **Type normally**: Match the lesson text character by character
- **Enter/Return**: Press when you see the `↵` symbol to match line breaks
- **Backspace**: Fix mistakes by going back
- **ESC**: Quit the current lesson early
- **Ctrl+C**: Also quits

### On Summary Screen
- **R**: Repeat the current lesson
- **M**: Practice your mistakes (creates lesson from top 10 mistyped words)
- **N**: New text (library mode only - loads a new random text from the library)
- **B**: Go back to previous lesson in the stack
- **Q**: Quit the program

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
5. **Completion**: When you finish, see a summary screen with:
   - Final statistics (Time, WPM, Accuracy)
   - Top 10 most mistyped words with error counts
   - Options: R (repeat), M (practice mistakes), N (new text - library mode only), B (go back), Q (quit)
6. **Practice mistakes**: Press M to create a focused lesson from your top 10 mistyped words
   - Words are repeated 3 times using "bag shuffle" (each bag shuffled independently)
   - Example: mistakes ["a", "b"] → possible lesson: "b a a b b a"
   - Can practice mistakes of mistakes for unlimited nesting
7. **Go back**: Press B to return to previous lesson in the stack

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

### Practice with random TypeRacer texts

```bash
# Random text from the TypeRacer library
./just_type_it.py --library texts

# Combine with shuffle for word randomization
./just_type_it.py -l texts -s

# Repeat the same random text 5 times, shuffled
./just_type_it.py -l texts -r 5 -s
```

### Create a varied practice session

```bash
./just_type_it.py -t sample_lesson.txt -r 3 -s
```

### Quick drill with repeated phrases

```bash
./just_type_it.py -i "the quick brown fox" -r 10
```

### Practice workflow example

```
1. Start with a lesson: ./just_type_it.py -t sample_lesson.txt
2. After completing, see your mistakes in the summary
3. Press M to practice just those mistyped words
4. Complete the mistake lesson and press M again for nested practice
5. Press B to go back to the previous mistake lesson
6. Press B again to return to the original lesson
7. Press Q to quit
```

### Library mode workflow

```
1. Start with library: ./just_type_it.py -l texts
2. Complete the text and view your stats
3. Press N to load a brand new random text from the library
4. Press M to practice mistakes from the current text
5. Press N again to get another random text
6. Press B to go back to previous texts or mistake lessons
7. Press Q to quit
```

## Tips

- Start with short texts to warm up
- Use `--library texts` to practice with random TypeRacer texts for endless variety
- In library mode, press N after each lesson to quickly move to a new random text
- Press B to go back through your history of random texts and mistake lessons
- Use `--repeats` to build muscle memory for specific words or phrases
- Use `--shuffle` to prevent memorizing the exact order
- Remember: you must backspace to fix mistakes - this builds accuracy!
- Press M to practice your mistake words - this is the fastest way to improve
- Use nested mistake practice to drill down on your hardest words
- The bag shuffle pattern ensures balanced practice of all mistake words

## License

MIT

## Contributing

Issues and pull requests welcome!
