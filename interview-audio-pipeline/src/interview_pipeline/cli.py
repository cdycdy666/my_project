from __future__ import annotations

import argparse
import json

from .bos_storage import BosStorageClient
from .config import load_settings
from .notion_client import NotionClient
from .pipeline import execute_pipeline
from .qianfan_media_insight import QianfanMediaInsightService
from .web import serve_web_app


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(args)
        return
    if args.command == "inspect-mcp":
        inspect_mcp(args)
        return
    if args.command == "inspect-notion":
        inspect_notion(args)
        return
    if args.command == "upload-bos":
        upload_bos(args)
        return
    if args.command == "web":
        run_web(args)
        return

    raise SystemExit(f"Unsupported command: {args.command}")


def run_pipeline(args: argparse.Namespace) -> None:
    outcome = execute_pipeline(
        env_file=args.env_file,
        audio_file=args.audio_file,
        audio_url=args.audio_url,
        candidate=args.candidate,
        role=args.role,
        round_name=args.round,
        interview_date_text=args.date,
        write_to_notion=not args.dry_run,
        include_mock_review=False,
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "interview": {
                        "candidate": outcome.interview.candidate,
                        "role": outcome.interview.role,
                        "round": outcome.interview.round,
                        "date": outcome.interview.interview_date.isoformat(),
                        "audio_url": outcome.interview.audio_url,
                    },
                    "result": {
                        "task_id": outcome.result.task_id,
                        "status": outcome.result.status,
                        "summary": outcome.assessment.summary,
                        "recommendation": outcome.assessment.recommendation,
                    },
                    "page_markdown": outcome.page_markdown,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if outcome.notion_page is None:
        raise RuntimeError("Notion write was requested, but no Notion page was returned.")
    print(
        json.dumps(
            {
                "page_id": outcome.notion_page["id"],
                "page_url": outcome.notion_page["url"],
                "task_id": outcome.result.task_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def inspect_mcp(args: argparse.Namespace) -> None:
    settings = load_settings(env_file=args.env_file, require_notion=False)
    if not settings.qianfan.bearer_token:
        raise RuntimeError("QIANFAN_BEARER_TOKEN is required for inspect-mcp.")
    media_service = QianfanMediaInsightService(settings.qianfan)
    print(json.dumps(media_service.describe_tools(), ensure_ascii=False, indent=2))


def inspect_notion(args: argparse.Namespace) -> None:
    settings = load_settings(env_file=args.env_file, require_notion=True)
    if settings.notion is None:
        raise RuntimeError("Notion configuration is required for inspect-notion.")
    notion_client = NotionClient(settings.notion)
    print(json.dumps(notion_client.inspect_database(), ensure_ascii=False, indent=2))


def upload_bos(args: argparse.Namespace) -> None:
    settings = load_settings(env_file=args.env_file, require_notion=False)
    if settings.bos is None:
        raise RuntimeError(
            "BOS configuration is required. Set BOS_ACCESS_KEY_ID / BOS_SECRET_ACCESS_KEY / BOS_BUCKET / BOS_ENDPOINT."
        )
    client = BosStorageClient(settings.bos)
    result = client.upload_file(args.audio_file)
    print(
        json.dumps(
            {
                "object_key": result.object_key,
                "signed_url": result.signed_url,
                "public_url": result.public_url,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def run_web(args: argparse.Namespace) -> None:
    serve_web_app(host=args.host, port=args.port, env_file=args.env_file)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="interview-pipeline",
        description="Process interview recording and write the result to Notion.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Process a single interview recording")
    audio_group = run_parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio-url", help="Publicly downloadable recording URL")
    audio_group.add_argument("--audio-file", help="Local recording file path. Recommended for local_whisper.")
    run_parser.add_argument("--candidate", default="", help="Optional candidate name")
    run_parser.add_argument("--role", default="", help="Optional interview role. Defaults to 待补充.")
    run_parser.add_argument("--round", default="", help="Optional interview round. Will infer from file name when possible.")
    run_parser.add_argument("--date", default="", help="Optional interview date in YYYY-MM-DD format. Will infer from file name when possible.")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the pipeline without writing to Notion",
    )
    run_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Defaults to .env",
    )

    inspect_mcp_parser = subparsers.add_parser(
        "inspect-mcp",
        help="List media-insight MCP tools and show current auto-selection",
    )
    inspect_mcp_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Defaults to .env",
    )

    inspect_notion_parser = subparsers.add_parser(
        "inspect-notion",
        help="Inspect the target Notion database schema and validate property mappings",
    )
    inspect_notion_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Defaults to .env",
    )

    upload_bos_parser = subparsers.add_parser(
        "upload-bos",
        help="Upload a local audio file to BOS and return a signed download URL",
    )
    upload_bos_parser.add_argument("--audio-file", required=True, help="Local recording file path")
    upload_bos_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Defaults to .env",
    )

    web_parser = subparsers.add_parser(
        "web",
        help="Start a local frontend for upload and review",
    )
    web_parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Defaults to 127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8787, help="Port to bind. Defaults to 8787")
    web_parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file. Defaults to .env",
    )
    return parser


if __name__ == "__main__":
    main()
