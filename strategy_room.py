from __future__ import annotations

import argparse
import asyncio
import json
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sc2 import maps
from sc2.data import Race
from sc2.main import GameMatch, maintain_SCII_count, run_game, run_match
from sc2.player import Bot, BotProcess
from sc2.sc2process import SC2Process, logger, paths

from strategy_loader import discover_bot_class, instantiate_bot

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ROOM_DIR = REPO_ROOT / ".strategy_room"

RACE_MAP = {
    "protoss": Race.Protoss,
    "terran": Race.Terran,
    "zerg": Race.Zerg,
    "random": Race.Random,
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-")
    return slug or "player"


def json_response(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url=url, method=method, data=data, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_server_url(server: str) -> str:
    if server.startswith("http://") or server.startswith("https://"):
        return server.rstrip("/")
    return f"http://{server.rstrip('/')}"


def discover_join_hosts(bind_host: str) -> list[str]:
    if bind_host not in {"0.0.0.0", "::"}:
        return [bind_host]

    hosts = ["127.0.0.1"]
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This never sends traffic, it only asks the OS which local IP would be used.
        udp_socket.connect(("8.8.8.8", 80))
        local_ip = udp_socket.getsockname()[0]
        if local_ip not in hosts:
            hosts.append(local_ip)
    except OSError:
        pass
    finally:
        udp_socket.close()
    return hosts


def activate_starcraft_windows() -> None:
    if platform.system() != "Darwin":
        return
    subprocess.run(
        ["osascript", "-e", 'tell application id "com.blizzard.starcraft2" to activate'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def focus_starcraft_windows(stop_event: threading.Event, attempts: int = 12, interval: float = 1.0) -> None:
    for _ in range(attempts):
        if stop_event.is_set():
            return
        activate_starcraft_windows()
        time.sleep(interval)


class VisibleMacSC2Process(SC2Process):
    def _launch(self):
        if platform.system() != "Darwin":
            return super()._launch()

        if self._sc2_version and not self._base_build:
            self._base_build = self.find_base_dir(self._sc2_version)

        if self._base_build:
            executable = str(paths.latest_executeble(paths.Paths.BASE / "Versions", self._base_build))
        else:
            executable = str(paths.Paths.EXECUTABLE)

        app_bundle = Path(executable).parents[2]
        sc2_args = [
            "-listen",
            self._serverhost,
            "-port",
            str(self._port),
            "-dataDir",
            str(paths.Paths.BASE),
            "-tempDir",
            self._tmp_dir,
        ]
        for arg, value in self._arguments.items():
            sc2_args.extend([arg, value])

        if self._sc2_version:
            def special_match(version_string: str) -> bool:
                return any(version["label"] == version_string for version in self.versions)

            if special_match(self._sc2_version):
                self._data_hash = self.find_data_hash(self._sc2_version)
                assert self._data_hash is not None
            else:
                logger.warning(
                    f'The submitted version string in sc2.rungame() function call (sc2_version="{self._sc2_version}") '
                    "was not found in versions.py. Running latest version instead."
                )

        if self._data_hash:
            sc2_args.extend(["-dataVersion", self._data_hash])

        sc2_args.append("-verbose")
        return subprocess.Popen(
            ["open", "-nW", str(app_bundle), "--args", *sc2_args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _clean(self, verbose: bool = True) -> None:
        super()._clean(verbose=verbose)
        if platform.system() != "Darwin":
            return
        if self._port is None:
            return
        subprocess.run(
            ["pkill", "-f", f"{paths.Paths.EXECUTABLE}.*-port {self._port}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


@dataclass
class Participant:
    name: str
    race: str
    bot_path: Path
    class_name: str
    log_path: Path
    joined_at: str


class RoomServer:
    def __init__(
        self,
        host: str,
        port: int,
        expected_players: int,
        map_name: str,
        room_dir: Path,
        realtime: bool = True,
        game_time_limit: int | None = None,
        visible: bool = True,
        window_width: int = 960,
        window_height: int = 540,
        window_left: int = 40,
        window_top: int = 40,
        window_gap: int = 32,
    ):
        if expected_players < 2:
            raise ValueError("expected_players must be at least 2")

        self.host = host
        self.port = port
        self.expected_players = expected_players
        self.map_name = map_name
        self.realtime = realtime
        self.game_time_limit = game_time_limit
        self.visible = visible
        self.window_width = window_width
        self.window_height = window_height
        self.window_left = window_left
        self.window_top = window_top
        self.window_gap = window_gap
        self.room_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.room_dir = room_dir.resolve() / self.room_id
        self.participants_dir = self.room_dir / "participants"
        self.logs_dir = self.room_dir / "logs"
        self.room_dir.mkdir(parents=True, exist_ok=True)
        self.participants_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.lock = threading.Lock()
        self.participants: list[Participant] = []
        self.started = False
        self.pending_start = False
        self.finished = False
        self.error: str | None = None
        self.results: dict[str, str | None] | None = None

    def status(self) -> dict:
        with self.lock:
            return {
                "room_id": self.room_id,
                "host": self.host,
                "port": self.port,
                "map": self.map_name,
                "realtime": self.realtime,
                "visible": self.visible,
                "expected_players": self.expected_players,
                "joined_players": len(self.participants),
                "started": self.started,
                "pending_start": self.pending_start,
                "finished": self.finished,
                "error": self.error,
                "results": self.results,
                "participants": [
                    {
                        "name": participant.name,
                        "race": participant.race,
                        "class_name": participant.class_name,
                        "joined_at": participant.joined_at,
                        "bot_path": str(participant.bot_path),
                        "log_path": str(participant.log_path),
                    }
                    for participant in self.participants
                ],
            }

    def register(self, name: str, race: str, bot_source: str) -> dict:
        if race not in RACE_MAP:
            raise ValueError(f"Unsupported race: {race}")

        with self.lock:
            if self.started:
                raise RuntimeError("The room already started the match")
            if len(self.participants) >= self.expected_players:
                raise RuntimeError("The room is already full")
            if any(existing.name == name for existing in self.participants):
                raise RuntimeError(f"Player name {name!r} is already in use")

            participant_slug = slugify(name)
            participant_dir = self.participants_dir / participant_slug
            if participant_dir.exists():
                raise RuntimeError(f"Participant directory already exists: {participant_dir}")

            participant_dir.mkdir(parents=True, exist_ok=False)
            bot_path = participant_dir / "bot.py"
            bot_path.write_text(bot_source, encoding="utf-8")

            try:
                bot_class = discover_bot_class(bot_path)
            except Exception:
                shutil.rmtree(participant_dir, ignore_errors=True)
                raise

            participant = Participant(
                name=name,
                race=race,
                bot_path=bot_path,
                class_name=bot_class.__name__,
                log_path=self.logs_dir / f"{participant_slug}.log",
                joined_at=datetime.now().isoformat(timespec="seconds"),
            )
            self.participants.append(participant)

            should_start = len(self.participants) == self.expected_players and not self.started
            if should_start:
                self.started = True
                self.pending_start = True

            return {
                "accepted": True,
                "name": participant.name,
                "race": participant.race,
                "class_name": participant.class_name,
                "joined_players": len(self.participants),
                "expected_players": self.expected_players,
                "match_started": should_start,
                "room_id": self.room_id,
            }

    def process_config(self, index: int) -> dict:
        if not self.visible:
            return {}

        x_position = self.window_left + index * (self.window_width + self.window_gap)
        return {
            "fullscreen": False,
            "resolution": (self.window_width, self.window_height),
            "placement": (x_position, self.window_top),
        }

    def consume_pending_start(self) -> bool:
        with self.lock:
            if not self.pending_start:
                return False
            self.pending_start = False
            return True

    def run_match_blocking(self):
        if self.visible:
            self._run_visible_match_blocking()
            return

        try:
            asyncio.run(self._run_headless_match())
        except Exception as exc:
            with self.lock:
                self.error = f"{type(exc).__name__}: {exc}"
                self.finished = True

    def _run_visible_match_blocking(self):
        participants = list(self.participants)
        if not participants:
            with self.lock:
                self.error = "No participants to run"
                self.finished = True
            return

        map_settings = maps.get(self.map_name)
        players = [
            Bot(
                RACE_MAP[participant.race],
                instantiate_bot(participant.bot_path, class_name=participant.class_name),
                name=participant.name,
            )
            for participant in participants
        ]

        focus_stop_event = threading.Event()
        focus_thread = threading.Thread(
            target=focus_starcraft_windows,
            args=(focus_stop_event,),
            name="sc2-focus",
            daemon=True,
        )
        focus_thread.start()

        try:
            raw_result = run_game(
                map_settings,
                players,
                realtime=self.realtime,
                game_time_limit=self.game_time_limit,
            )
        except Exception as exc:
            with self.lock:
                self.error = f"{type(exc).__name__}: {exc}"
                self.finished = True
            return
        finally:
            focus_stop_event.set()
            focus_thread.join(timeout=1)

        if not isinstance(raw_result, list):
            raw_result = [raw_result]

        serialized = {}
        for participant, result in zip(participants, raw_result):
            serialized[participant.name] = None if result is None else result.name

        with self.lock:
            self.results = serialized
            self.finished = True

    async def _run_headless_match(self):
        participants = list(self.participants)
        if not participants:
            with self.lock:
                self.error = "No participants to run"
                self.finished = True
            return

        map_settings = maps.get(self.map_name)
        players = [
            BotProcess(
                path=str(REPO_ROOT),
                launch_list=[
                    sys.executable,
                    str(REPO_ROOT / "uploaded_bot_runner.py"),
                    "--bot-file",
                    str(participant.bot_path),
                    "--race",
                    participant.race,
                    "--class-name",
                    participant.class_name,
                    "--name",
                    participant.name,
                ],
                race=RACE_MAP[participant.race],
                name=participant.name,
                stdout=str(participant.log_path),
            )
            for participant in participants
        ]

        match = GameMatch(
            map_sc2=map_settings,
            players=players,
            realtime=self.realtime,
            game_time_limit=self.game_time_limit,
        )

        controllers = []
        try:
            for index in range(match.needed_sc2_count):
                process = SC2Process(**self.process_config(index))
                controller = await process.__aenter__()
                controllers.append(controller)
            if self.visible:
                activate_starcraft_windows()
            raw_result = await run_match(controllers, match, close_ws=True)
        finally:
            await maintain_SCII_count(0, controllers)

        with self.lock:
            if raw_result is None:
                self.error = "Match execution returned no result"
                self.finished = True
                return

            serialized = {}
            for player, result in raw_result.items():
                if player is None:
                    continue
                player_name = player.name if getattr(player, "name", None) else str(player)
                serialized[player_name] = None if result is None else result.name

            self.results = serialized
            self.finished = True


class RoomRequestHandler(BaseHTTPRequestHandler):
    room_server: RoomServer | None = None

    def send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return

    def do_GET(self):
        if self.room_server is None:
            self.send_json(500, {"error": "Room server is not initialized"})
            return

        path = urlparse(self.path).path
        if path != "/status":
            self.send_json(404, {"error": "Unknown endpoint"})
            return

        self.send_json(200, self.room_server.status())

    def do_POST(self):
        if self.room_server is None:
            self.send_json(500, {"error": "Room server is not initialized"})
            return

        path = urlparse(self.path).path
        if path != "/join":
            self.send_json(404, {"error": "Unknown endpoint"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            name = payload["name"].strip()
            race = payload.get("race", "protoss").strip().lower()
            bot_source = payload["bot_source"]
            if not name:
                raise ValueError("name must not be empty")
            response = self.room_server.register(name=name, race=race, bot_source=bot_source)
            self.send_json(200, response)
        except KeyError as exc:
            self.send_json(400, {"error": f"Missing field: {exc.args[0]}"})
        except Exception as exc:
            self.send_json(400, {"error": str(exc)})


def serve_room(args):
    if args.players != 2:
        raise SystemExit(
            "SC2 API only supports uploaded multi-agent bot matches as 1v1. "
            "Use `python strategy_room.py server --players 2 --map AcropolisLE`."
        )

    room_server = RoomServer(
        host=args.host,
        port=args.port,
        expected_players=args.players,
        map_name=args.map,
        room_dir=Path(args.room_dir),
        realtime=args.realtime,
        game_time_limit=args.game_time_limit,
        visible=args.visible,
        window_width=args.window_width,
        window_height=args.window_height,
        window_left=args.window_left,
        window_top=args.window_top,
        window_gap=args.window_gap,
    )
    RoomRequestHandler.room_server = room_server
    httpd = ThreadingHTTPServer((args.host, args.port), RoomRequestHandler)
    http_thread = threading.Thread(target=httpd.serve_forever, name="room-http", daemon=True)
    http_thread.start()
    join_hosts = discover_join_hosts(args.host)

    print(
        json.dumps(
            {
                "message": "Room server started",
                "join_url": f"http://{join_hosts[0]}:{args.port}/join",
                "status_url": f"http://{join_hosts[0]}:{args.port}/status",
                "join_urls": [f"http://{host}:{args.port}/join" for host in join_hosts],
                "room_dir": str(room_server.room_dir),
                "expected_players": args.players,
                "map": args.map,
                "realtime": args.realtime,
                "visible": args.visible,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    try:
        while True:
            if room_server.consume_pending_start():
                room_server.run_match_blocking()
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
        http_thread.join(timeout=5)


def join_room(args):
    server = normalize_server_url(args.server)
    bot_file = Path(args.bot_file).resolve()
    payload = {
        "name": args.name,
        "race": args.race,
        "bot_source": bot_file.read_text(encoding="utf-8"),
    }

    response = json_response(f"{server}/join", method="POST", payload=payload)
    print(json.dumps(response, ensure_ascii=False, indent=2))

    if not args.watch:
        return

    while True:
        time.sleep(args.poll_interval)
        status = json_response(f"{server}/status")
        print(json.dumps(status, ensure_ascii=False, indent=2))
        if status.get("finished") or status.get("error"):
            return


def room_status(args):
    server = normalize_server_url(args.server)
    response = json_response(f"{server}/status")
    print(json.dumps(response, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Upload-only strategy room for SC2 bot matches",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    server_parser = subparsers.add_parser("server", help="Run the room host")
    server_parser.add_argument("--host", default="0.0.0.0")
    server_parser.add_argument("--port", type=int, default=8765)
    server_parser.add_argument("--players", "--player", type=int, default=2)
    server_parser.add_argument("--map", default="AcropolisLE")
    server_parser.add_argument("--room-dir", default=str(DEFAULT_ROOM_DIR))
    server_parser.add_argument("--game-time-limit", type=int)
    server_parser.add_argument("--realtime", dest="realtime", action="store_true")
    server_parser.add_argument("--step-mode", dest="realtime", action="store_false")
    server_parser.add_argument("--visible", dest="visible", action="store_true")
    server_parser.add_argument("--headless", dest="visible", action="store_false")
    server_parser.add_argument("--window-width", type=int, default=960)
    server_parser.add_argument("--window-height", type=int, default=540)
    server_parser.add_argument("--window-left", type=int, default=40)
    server_parser.add_argument("--window-top", type=int, default=40)
    server_parser.add_argument("--window-gap", type=int, default=32)
    server_parser.set_defaults(realtime=True, visible=True)
    server_parser.set_defaults(handler=serve_room)

    join_parser = subparsers.add_parser("join", help="Upload a local bot.py to a room host")
    join_parser.add_argument("--server", required=True, help="e.g. 192.168.0.10:8765")
    join_parser.add_argument("--name", required=True)
    join_parser.add_argument("--race", default="protoss", choices=tuple(RACE_MAP.keys()))
    join_parser.add_argument("--bot-file", default="bot.py")
    join_parser.add_argument("--watch", action="store_true")
    join_parser.add_argument("--poll-interval", type=int, default=5)
    join_parser.set_defaults(handler=join_room)

    status_parser = subparsers.add_parser("status", help="Show room status")
    status_parser.add_argument("--server", required=True, help="e.g. 192.168.0.10:8765")
    status_parser.set_defaults(handler=room_status)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.handler(args)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise SystemExit(f"Could not reach server: {exc.reason}") from exc


if __name__ == "__main__":
    main()
