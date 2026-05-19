from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_VIDEO = Path("/Users/chendingyu/my_project/video/raw_video/抖音2026430-284326.mp4")
ASSETS_DIR = PROJECT_DIR / "assets"
VOICE_DIR = PROJECT_DIR / "voice"
SUBTITLES_DIR = PROJECT_DIR / "subtitles"
EXPORTS_DIR = PROJECT_DIR / "exports"

CLIP_START = 36.0
CLIP_DURATION = 44.0
TTS_SWIFT = PROJECT_DIR / "tts_to_file.swift"

LINES = [
    {"start": 0.2, "text": "玄骨你先冷静，这把真不能接。"},
    {"start": 4.0, "text": "对面韩立，主角，你碰他等于提前领盒饭。"},
    {"start": 9.1, "text": "又是辟邪神雷？别数了，他金雷竹飞剑跟批发的一样。"},
    {"start": 14.8, "text": "现在跑还来得及，鼎先别要了，命比面子重要。"},
    {"start": 20.7, "text": "不是，修罗圣火你都敢掏？你是真想现场领便当啊。"},
    {"start": 26.8, "text": "玄骨，活了几百年了，你见过哪个反派能单杀主角？"},
    {"start": 33.3, "text": "快停，这不是斗法，这是给韩立补高光镜头。"},
    {"start": 39.2, "text": "行了，认栽吧，至少还能少挨两道神雷。"},
]


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def probe_duration(path: Path) -> float:
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


def format_ts(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours = millis // 3_600_000
    minutes = (millis % 3_600_000) // 60_000
    secs = (millis % 60_000) // 1000
    ms = millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def ensure_dirs() -> None:
    for path in (ASSETS_DIR, VOICE_DIR, SUBTITLES_DIR, EXPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def cut_clip() -> Path:
    clip_path = ASSETS_DIR / "source_clip.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(CLIP_START),
            "-t",
            str(CLIP_DURATION),
            "-i",
            str(SOURCE_VIDEO),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(clip_path),
        ]
    )
    return clip_path


def synthesize_voice() -> list[dict[str, float | str]]:
    enriched: list[dict[str, float | str]] = []
    for idx, line in enumerate(LINES, start=1):
        out_path = VOICE_DIR / f"line_{idx:02d}.wav"
        run(
            [
                "swift",
                str(TTS_SWIFT),
                str(out_path),
                str(line["text"]),
            ]
        )
        duration = probe_duration(out_path)
        enriched.append(
            {
                "index": idx,
                "start": float(line["start"]),
                "text": str(line["text"]),
                "path": str(out_path),
                "duration": duration,
            }
        )
    (VOICE_DIR / "segments.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return enriched


def write_srt(segments: list[dict[str, float | str]]) -> Path:
    srt_path = SUBTITLES_DIR / "sample.srt"
    blocks: list[str] = []
    for idx, segment in enumerate(segments):
        start = float(segment["start"])
        natural_end = start + float(segment["duration"]) + 0.25
        next_start = (
            float(segments[idx + 1]["start"]) - 0.12
            if idx + 1 < len(segments)
            else CLIP_DURATION - 0.1
        )
        end = min(natural_end, next_start)
        blocks.append(
            "\n".join(
                [
                    str(idx + 1),
                    f"{format_ts(start)} --> {format_ts(end)}",
                    str(segment["text"]),
                ]
            )
        )
    srt_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return srt_path


def render_video(clip_path: Path, segments: list[dict[str, float | str]], srt_path: Path) -> Path:
    output_path = EXPORTS_DIR / "玄骨星际穿越_样片.mp4"

    input_args = ["-i", str(clip_path)]
    filter_parts = ["[0:a]volume=0.06[bg]"]
    mix_inputs = ["[bg]"]

    for input_index, segment in enumerate(segments, start=1):
        input_args.extend(["-i", str(segment["path"])])
        delay_ms = int(round(float(segment["start"]) * 1000))
        filter_parts.append(
            f"[{input_index}:a]adelay={delay_ms}|{delay_ms},volume=1.45[a{input_index}]"
        )
        mix_inputs.append(f"[a{input_index}]")

    filter_parts.append(
        "".join(mix_inputs) + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[mix]"
    )
    audio_filter = ";".join(filter_parts)
    subtitle_filter = (
        "subtitles=subtitles/sample.srt:"
        "force_style='FontName=PingFang SC,FontSize=21,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00302010,BorderStyle=3,Outline=2,Shadow=0,MarginV=54,Alignment=2'"
    )

    run(
        [
            "ffmpeg",
            "-y",
            *input_args,
            "-filter_complex",
            audio_filter,
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ],
        cwd=PROJECT_DIR,
    )
    return output_path


def main() -> None:
    ensure_dirs()
    clip_path = cut_clip()
    segments = synthesize_voice()
    srt_path = write_srt(segments)
    output_path = render_video(clip_path, segments, srt_path)
    print(output_path)


if __name__ == "__main__":
    main()
