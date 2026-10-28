# Audio Bookmark Splitter

Split one audio file into one output file per bookmark in a SABP XML file. Each output is named with the bookmark title.

## Prerequisites
- Python 3.11.2 or newer
- `ffmpeg.exe` and `ffprobe.exe` in the project directory

## Setup
Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available, then create the project environment and install dependencies:
```
   uv sync
```
This creates a `.venv` environment from `pyproject.toml` and `uv.lock`.

## How to Use
Run the script with `uv run`. By default, it looks for `bookmarks.sabp.xml` beside the audio and saves the split files in that same folder:
```
   uv run python audio_splitter_final.py "path\to\file.m4a"
```
You can specify a different bookmark file or output folder:
```
   uv run python audio_splitter_final.py "path\to\file.m4a" --bookmarks "path\to\bookmarks.sabp.xml" --output "path\to\output\split"
```
To convert the split files to MP3, add `--format mp3` (or `--output-format mp3`):
```
   uv run python audio_splitter_final.py "path\to\file.m4a" --format mp3
```

## Features
- Splits at the bookmark positions, using each title for its output filename
- Interprets `filePosition` as seconds
- Includes any audio before the first bookmark in the first output; the last output runs to the end of the source
- Keeps the source format by default; `--format mp3` converts each segment to MP3
- Supports common audio formats supported by FFmpeg (m4a, mp3, wav, etc.)
- Shows progress bar during processing

## Tested On
Python 3.11.2