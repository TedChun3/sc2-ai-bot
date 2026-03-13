from __future__ import annotations

import argparse

from sc2 import maps
from sc2.data import Race
from sc2.main import run_game
from sc2.player import Bot

from strategy_loader import instantiate_bot

RACE_MAP = {
    "protoss": Race.Protoss,
    "terran": Race.Terran,
    "zerg": Race.Zerg,
    "random": Race.Random,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local SC2 bot-vs-bot duel using the same run_game path as bot.py",
        allow_abbrev=False,
    )
    parser.add_argument("--bot1-file", default="bot.py")
    parser.add_argument("--bot2-file", default="bot.py")
    parser.add_argument("--bot1-class-name")
    parser.add_argument("--bot2-class-name")
    parser.add_argument("--bot1-name", default="player1")
    parser.add_argument("--bot2-name", default="player2")
    parser.add_argument("--bot1-race", default="protoss", choices=tuple(RACE_MAP.keys()))
    parser.add_argument("--bot2-race", default="protoss", choices=tuple(RACE_MAP.keys()))
    parser.add_argument("--map", default="AcropolisLE")
    parser.add_argument("--realtime", dest="realtime", action="store_true")
    parser.add_argument("--step-mode", dest="realtime", action="store_false")
    parser.add_argument("--save-replay")
    parser.add_argument("--game-time-limit", type=int)
    parser.set_defaults(realtime=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    bot1 = Bot(
        RACE_MAP[args.bot1_race],
        instantiate_bot(args.bot1_file, class_name=args.bot1_class_name),
        name=args.bot1_name,
    )
    bot2 = Bot(
        RACE_MAP[args.bot2_race],
        instantiate_bot(args.bot2_file, class_name=args.bot2_class_name),
        name=args.bot2_name,
    )

    result = run_game(
        maps.get(args.map),
        [bot1, bot2],
        realtime=args.realtime,
        save_replay_as=args.save_replay,
        game_time_limit=args.game_time_limit,
    )
    print(result)


if __name__ == "__main__":
    main()
