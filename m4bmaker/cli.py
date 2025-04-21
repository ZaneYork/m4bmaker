import argparse
import json
from pathlib import Path

from m4bmaker import M4BMaker


def cli() -> None:
    """Command line interface for m4bmaker."""

    parser = argparse.ArgumentParser(
        description="m4bmaker: A tool for creating .m4b audiobooks from audio tracks."
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path.cwd() / "m4bmaker.json",
        help="Path to the JSON configuration file (default: ./m4bmaker.json).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["json", "single", "chapter"],
        default="json",
        help="Mode of operation: 'json', 'single', or 'chapter' (default: 'json').",
    )
    parser.add_argument(
        "--output-bitrate",
        type=str,
        choices=["64k", "128k"],
        default="64k",
        help="Output audio bitrate: '64k' or '128k' (default: '64k').",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path.cwd() / "m4bmaker.log",
        help="Path to the log file (default: ./m4bmaker.log).",
    )

    subparsers = parser.add_subparsers(dest="subparser_name")
    subparsers.add_parser("to_dict", help="Shows the audiobook data as a dictionary.")
    subparsers.add_parser("convert", help="Converts the audiobook to .m4b format.")

    args = parser.parse_args()
    try:
        if args.subparser_name is None:
            parser.print_help()
            return

        m4b = M4BMaker(
            json_path=args.json_path,
            mode=args.mode,
            output_bitrate=args.output_bitrate,
            log_path=args.log_path,
        )
        if args.subparser_name == "to_dict":
            print(json.dumps(m4b.to_dict(), indent=2))
        if args.subparser_name == "convert":
            m4b.convert()
    except Exception as e:
        print(f"Error: {e}")
