#!/usr/bin/env python3
"""
Podcast Editor - Two modes:
  shorts  : Portrait 9:16 reels from Zoom recording
  full    : Full landscape episode with animated background

Usage:
  Shorts (single segment):
    python podcast_editor.py --mode shorts --input zoom.mp4 --segments 02:15-03:45

  Shorts (multiple segments):
    python podcast_editor.py --mode shorts --input zoom.mp4 --segments 02:15-03:45,10:00-11:30

  Full episode:
    python podcast_editor.py --mode full --input zoom.mp4 --bg background.mp4

Output files go to ./output/ folder.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], label: str):
    """Run an ffmpeg command and exit on failure."""
    print(f"\n▶ {label}")
    print("  " + " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n✗ ffmpeg error:\n{result.stderr[-2000:]}")
        sys.exit(1)
    print(f"  ✓ Done")


def ts_to_seconds(ts: str) -> float:
    """Convert MM:SS or HH:MM:SS to seconds."""
    parts = ts.strip().split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Invalid timestamp: {ts}")


def parse_segments(segments_str: str) -> list[tuple[float, float]]:
    """Parse '02:15-03:45,10:00-11:30' into list of (start_sec, end_sec)."""
    segments = []
    for seg in segments_str.split(","):
        seg = seg.strip()
        if "-" not in seg:
            raise ValueError(f"Invalid segment format: {seg}. Use START-END e.g. 02:15-03:45")
        start_str, end_str = seg.split("-", 1)
        start = ts_to_seconds(start_str)
        end = ts_to_seconds(end_str)
        if end <= start:
            raise ValueError(f"End time must be after start time in segment: {seg}")
        segments.append((start, end))
    return segments


def make_shorts(input_path: str, segments: list[tuple[float, float]], output_dir: Path):
    """
    Mode 1 — Portrait 9:16 shorts.
    Layout: speaker (right half of Zoom) on top, host (left half) on bottom.
    Gap of ~80px in middle reserved for captions.
    Background: dark (#0d0d0d).

    Final output: 1080x1920
    Each speaker panel: 1080x880 (after scaling)
    Gap: 160px
    Total: 880 + 160 + 880 = 1920 ✓
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, (start, end) in enumerate(segments):
        duration = end - start
        output_file = output_dir / f"short_{i+1:02d}_{int(start)}s-{int(end)}s.mp4"

        # Filter complex breakdown:
        # 1. Crop left half (host/me) and right half (speaker) from 1280x720 source
        # 2. Scale each to 1080x880 (fills width, letterboxes height slightly)
        # 3. Create dark background 1080x1920
        # 4. Overlay speaker at top (y=0), host at bottom (y=1040), gap=160px in middle
        filter_complex = (
            "[0:v]crop=iw/2:ih:iw/2:0,scale=1080:880:force_original_aspect_ratio=decrease,"
            "pad=1080:880:(ow-iw)/2:(oh-ih)/2:color=#0d0d0d[speaker];"

            "[0:v]crop=iw/2:ih:0:0,scale=1080:880:force_original_aspect_ratio=decrease,"
            "pad=1080:880:(ow-iw)/2:(oh-ih)/2:color=#0d0d0d[host];"

            "color=#0d0d0d:s=1080x1920[bg];"

            "[bg][speaker]overlay=0:0[tmp];"
            "[tmp][host]overlay=0:1040[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            str(output_file)
        ]

        run(cmd, f"Short {i+1}/{len(segments)}: {start}s → {end}s")
        print(f"  → {output_file}")


def make_full_episode(input_path: str, bg_path: str, output_dir: Path):
    """
    Mode 2 — Full landscape 16:9 episode with animated background.
    Layout: host (left) and speaker (right) side by side with gap.
    Background: looping animation video.

    Final output: 1920x1080
    Each panel: 880x880 (square crops, scaled)
    Gap between panels: 160px
    Total width: 880 + 160 + 880 = 1920 ✓
    Vertical centering: (1080 - 880) / 2 = 100px top/bottom padding
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    input_name = Path(input_path).stem
    output_file = output_dir / f"{input_name}_episode.mp4"

    # Get duration of input
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    duration = float(probe.stdout.strip())
    print(f"\n  Input duration: {duration/60:.1f} minutes")
    print(f"  Estimated processing time: {duration/60 * 0.5:.0f}-{duration/60:.0f} minutes")
    print(f"  Output: {output_file}")

    # Filter complex breakdown:
    # [0] = zoom input, [1] = background video (looped)
    # 1. Loop background to match input duration, scale to 1920x1080, blur it
    # 2. Crop host (left half) → scale to 880x880 square
    # 3. Crop speaker (right half) → scale to 880x880 square
    # 4. Overlay host at x=0, y=100 (vertically centered)
    # 5. Overlay speaker at x=1040, y=100 (gap=160px)
    filter_complex = (
        # Background: loop, scale, add subtle blur/darken
        "[1:v]scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,setpts=PTS-STARTPTS[bgscaled];"
        "[bgscaled]eq=brightness=-0.1:saturation=0.8[bg];"

        # Host panel (left half of Zoom)
        "[0:v]crop=iw/2:ih:0:0,scale=880:880:force_original_aspect_ratio=decrease,"
        "pad=880:880:(ow-iw)/2:(oh-ih)/2:color=black@0[host];"

        # Speaker panel (right half of Zoom)
        "[0:v]crop=iw/2:ih:iw/2:0,scale=880:880:force_original_aspect_ratio=decrease,"
        "pad=880:880:(ow-iw)/2:(oh-ih)/2:color=black@0[speaker];"

        # Composite: bg → overlay host → overlay speaker
        "[bg][host]overlay=0:100[tmp];"
        "[tmp][speaker]overlay=1040:100[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-stream_loop", "-1", "-i", bg_path,  # loop background infinitely
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",  # stop when zoom input ends
        str(output_file)
    ]

    run(cmd, f"Full episode: {duration/60:.1f} min → {output_file.name}")
    print(f"\n  ✓ Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Podcast Editor — Shorts and Full Episode modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--mode", required=True, choices=["shorts", "full"],
                        help="'shorts' for portrait reels, 'full' for landscape episode")
    parser.add_argument("--input", required=True,
                        help="Path to Zoom recording MP4")
    parser.add_argument("--segments",
                        help="[shorts only] Comma-separated segments: 02:15-03:45,10:00-11:30")
    parser.add_argument("--bg",
                        help="[full only] Path to background animation MP4")
    parser.add_argument("--output", default="./output",
                        help="Output directory (default: ./output)")

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"✗ Input file not found: {args.input}")
        sys.exit(1)

    output_dir = Path(args.output)

    if args.mode == "shorts":
        if not args.segments:
            print("✗ --segments required for shorts mode")
            print("  Example: --segments 02:15-03:45,10:00-11:30")
            sys.exit(1)
        segments = parse_segments(args.segments)
        print(f"\n▶ Shorts mode: {len(segments)} segment(s)")
        make_shorts(args.input, segments, output_dir)
        print(f"\n✓ All shorts saved to {output_dir}/")

    elif args.mode == "full":
        if not args.bg:
            print("✗ --bg required for full mode")
            print("  Example: --bg ~/Downloads/space_loop.mp4")
            sys.exit(1)
        if not os.path.exists(args.bg):
            print(f"✗ Background file not found: {args.bg}")
            sys.exit(1)
        print(f"\n▶ Full episode mode")
        make_full_episode(args.input, args.bg, output_dir)


if __name__ == "__main__":
    main()
