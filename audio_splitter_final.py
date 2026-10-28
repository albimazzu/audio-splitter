import argparse
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from tqdm import tqdm


FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
FFPROBE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffprobe.exe")


def load_bookmarks(bookmarks_file: str) -> list[tuple[str, int]]:
    root = ET.parse(bookmarks_file).getroot()
    bookmarks = []

    for bookmark in root.findall(".//bookmark"):
        title = (bookmark.findtext("title") or "").strip()
        position_text = bookmark.findtext("filePosition")
        if not position_text:
            raise ValueError("A bookmark is missing its filePosition.")

        try:
            position_seconds = float(position_text)
        except ValueError as exc:
            raise ValueError(f"Invalid bookmark position: {position_text!r}") from exc

        if not math.isfinite(position_seconds) or position_seconds < 0:
            raise ValueError(f"Invalid bookmark position: {position_text!r}")

        bookmarks.append((title, round(position_seconds * 1000)))

    if not bookmarks:
        raise ValueError(f"No bookmarks found in '{bookmarks_file}'.")

    bookmarks.sort(key=lambda item: item[1])
    for previous, current in zip(bookmarks, bookmarks[1:]):
        if current[1] <= previous[1]:
            raise ValueError("Bookmark positions must be unique.")

    return bookmarks


def safe_filename(title: str, index: int) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    if not safe_title:
        safe_title = f"bookmark_{index:02d}"
    return f"{index:02d} - {safe_title}"


def split_audio(
    input_file: str,
    output_folder: str,
    bookmarks_file: str | None = None,
    output_format: str | None = None,
) -> None:
    input_file = os.path.abspath(input_file)
    if bookmarks_file is None:
        bookmarks_file = os.path.join(
            os.path.dirname(input_file), "bookmarks.sabp.xml"
        )

    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Audio file not found: '{input_file}'.")
    if not os.path.isfile(bookmarks_file):
        raise FileNotFoundError(f"Bookmark file not found: '{bookmarks_file}'.")

    bookmarks = load_bookmarks(bookmarks_file)
    file_ext = os.path.splitext(input_file)[1].lstrip(".").lower()
    if not file_ext:
        raise ValueError("The audio file must have an extension.")
    output_ext = (output_format or file_ext).lower().lstrip(".")
    if output_ext != "mp3" and output_format is not None:
        raise ValueError("The only supported output format override is 'mp3'.")

    probe = subprocess.run(
        [
            FFPROBE_PATH,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_file,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration_ms = round(float(probe.stdout.strip()) * 1000)

    if bookmarks[0][1] >= duration_ms:
        raise ValueError("The first bookmark is at or beyond the end of the audio.")
    if any(position >= duration_ms for _, position in bookmarks):
        raise ValueError("A bookmark is at or beyond the end of the audio.")

    os.makedirs(output_folder, exist_ok=True)
    print(f"Splitting audio into {len(bookmarks)} bookmark-based files...")

    for index, (title, bookmark_position_ms) in enumerate(
        tqdm(bookmarks, desc="Processing bookmarks", unit="file"), start=1
    ):
        end_ms = (
            bookmarks[index][1] if index < len(bookmarks) else duration_ms
        )
        start_ms = 0 if index == 1 else bookmark_position_ms
        output_filename = f"{safe_filename(title, index)}.{output_ext}"
        output_path = os.path.join(output_folder, output_filename)
        start_seconds = start_ms / 1000
        length_seconds = (end_ms - start_ms) / 1000

        command = [
            FFMPEG_PATH,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            input_file,
            "-t",
            f"{length_seconds:.3f}",
            "-vn",
        ]
        if output_ext == "mp3":
            command.extend(["-c:a", "libmp3lame"])
        command.append(output_path)
        subprocess.run(command, check=True)

    print(f"\nDone! Created {len(bookmarks)} files in '{output_folder}'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split an audio file at the positions in a SABP bookmark XML."
    )
    parser.add_argument("input_file", help="Path to the source audio file.")
    parser.add_argument(
        "--bookmarks",
        help="Path to bookmarks.sabp.xml (defaults to that file beside the audio).",
    )
    parser.add_argument(
        "--output",
        help="Output folder (defaults to the source audio folder).",
    )
    parser.add_argument(
        "--format",
        "--output-format",
        dest="output_format",
        choices=["mp3"],
        help="Output format (defaults to the source audio format).",
    )
    args = parser.parse_args()

    output_folder = args.output or os.path.dirname(os.path.abspath(args.input_file))
    split_audio(
        args.input_file, output_folder, args.bookmarks, args.output_format
    )


if __name__ == "__main__":
    main()
