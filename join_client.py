from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def normalize_server_url(server: str) -> str:
    if server.startswith("http://") or server.startswith("https://"):
        return server.rstrip("/")
    return f"http://{server.rstrip('/')}"


def json_response(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url=url, method=method, data=data, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lightweight bot.py uploader for strategy_room",
        allow_abbrev=False,
    )
    parser.add_argument("--server", required=True, help="e.g. 192.168.0.10:8765")
    parser.add_argument("--name", required=True)
    parser.add_argument("--race", default="protoss", choices=("protoss", "terran", "zerg", "random"))
    parser.add_argument("--bot-file", default="bot.py")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    server = normalize_server_url(args.server)
    bot_file = Path(args.bot_file).resolve()
    payload = {
        "name": args.name,
        "race": args.race,
        "bot_source": bot_file.read_text(encoding="utf-8"),
    }

    try:
        response = json_response(f"{server}/join", method="POST", payload=payload)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach server: {exc.reason}") from exc

    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
