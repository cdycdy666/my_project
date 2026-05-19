#!/usr/bin/env python3
"""Generate retryable Yunxi narration segments, a stitched MP3, and VTT subtitles."""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import subprocess
from datetime import timedelta

import edge_tts


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def duration_seconds(path: pathlib.Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def vtt_time(seconds: float) -> str:
    td = timedelta(seconds=max(0, seconds))
    total_ms = int(td.total_seconds() * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}.{ms:03}"


async def synthesize_line(text: str, output: pathlib.Path, voice: str, rate: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(str(output))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="voice/narration.txt")
    parser.add_argument("--output", default="voice/narration-yunxi-clean-v1.mp3")
    parser.add_argument("--vtt", default="subtitles/narration-yunxi-clean-v1.vtt")
    parser.add_argument("--summary", default="voice/narration-yunxi-clean-v1-summary.json")
    parser.add_argument("--segments-dir", default="voice/segments-yunxi-clean-v1")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="-4%")
    parser.add_argument("--gap", type=float, default=0.12)
    parser.add_argument("--limit-lines", type=int, default=0)
    parser.add_argument("--scene-contract", default="")
    parser.add_argument("--group-by", choices=["line", "scene"], default="line")
    parser.add_argument("--limit-scenes", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project = pathlib.Path.cwd()
    input_path = project / args.input
    output_path = project / args.output
    vtt_path = project / args.vtt
    summary_path = project / args.summary
    segments_dir = project / args.segments_dir

    if args.group_by == "scene":
        if not args.scene_contract:
            raise SystemExit("--scene-contract is required when --group-by scene")
        contract = json.loads((project / args.scene_contract).read_text(encoding="utf-8"))
        scenes = contract["scenes"]
        if args.limit_scenes:
            scenes = scenes[: args.limit_scenes]
        if args.limit_lines:
            remaining = args.limit_lines
            groups = []
            for scene in scenes:
                scene_lines = [line.strip() for line in scene["narration_text"].splitlines() if line.strip()]
                if remaining <= 0:
                    break
                selected = scene_lines[:remaining]
                remaining -= len(selected)
                groups.append({"label": scene["scene_id"], "lines": selected})
        else:
            groups = [
                {"label": scene["scene_id"], "lines": [line.strip() for line in scene["narration_text"].splitlines() if line.strip()]}
                for scene in scenes
            ]
    else:
        lines = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if args.limit_lines:
            lines = lines[: args.limit_lines]
        groups = [{"label": f"{index:03d}", "lines": [line]} for index, line in enumerate(lines, start=1)]

    segments_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vtt_path.parent.mkdir(parents=True, exist_ok=True)

    segment_rows = []
    for index, group in enumerate(groups, start=1):
        segment = segments_dir / f"{index:03d}-{group['label']}.mp3"
        text = "\n".join(group["lines"])
        if args.force or not segment.exists():
            await synthesize_line(text, segment, args.voice, args.rate)
        segment_duration = duration_seconds(segment)
        segment_rows.append(
            {
                "index": index,
                "label": group["label"],
                "text": text,
                "lines": group["lines"],
                "path": str(segment.relative_to(project)),
                "duration": segment_duration,
            }
        )

    silence = segments_dir / "silence.mp3"
    if args.force or not silence.exists():
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=24000:cl=mono",
                "-t",
                str(args.gap),
                "-q:a",
                "9",
                "-acodec",
                "libmp3lame",
                str(silence),
            ]
        )

    concat_file = segments_dir / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as fh:
        for row in segment_rows:
            fh.write(f"file '{(project / row['path']).as_posix()}'\n")
            if row["index"] != len(segment_rows):
                fh.write(f"file '{silence.as_posix()}'\n")

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-b:a",
            "48k",
            str(output_path),
        ]
    )

    cursor = 0.0
    vtt_lines = ["WEBVTT", ""]
    cue_index = 1
    for row in segment_rows:
        start = cursor
        group_chars = sum(max(1, len(line)) for line in row["lines"])
        line_cursor = start
        for line in row["lines"]:
            line_duration = row["duration"] * (max(1, len(line)) / group_chars)
            line_end = min(start + row["duration"], line_cursor + line_duration)
            vtt_lines.extend(
                [
                    str(cue_index),
                    f"{vtt_time(line_cursor)} --> {vtt_time(line_end)}",
                    line,
                    "",
                ]
            )
            cue_index += 1
            line_cursor = line_end
        cursor = start + row["duration"] + args.gap
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")

    final_duration = duration_seconds(output_path)
    summary = {
        "voice": args.voice,
        "rate": args.rate,
        "group_by": args.group_by,
        "group_count": len(segment_rows),
        "line_count": sum(len(row["lines"]) for row in segment_rows),
        "gap_seconds": args.gap,
        "output": str(output_path.relative_to(project)),
        "vtt": str(vtt_path.relative_to(project)),
        "duration": final_duration,
        "segments": segment_rows,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
