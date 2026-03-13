from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ladder import run_ladder_game
from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

from strategy_loader import instantiate_bot

RACE_MAP = {
    "protoss": Race.Protoss,
    "terran": Race.Terran,
    "zerg": Race.Zerg,
    "random": Race.Random,
}


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--bot-file", required=True)
    parser.add_argument("--race", default="protoss", choices=tuple(RACE_MAP.keys()))
    parser.add_argument("--class-name")
    parser.add_argument("--name")
    return parser.parse_known_args()


if __name__ == "__main__":
    args, _unknown = parse_args()

    bot_file = Path(args.bot_file).resolve()
    ai = instantiate_bot(bot_file, class_name=args.class_name)
    bot = Bot(RACE_MAP[args.race], ai, name=args.name)

    if "--LadderServer" in sys.argv:
        result, opponent_id = run_ladder_game(bot)
        print(f"{result} against opponent {opponent_id}")
    else:
        result = run_game(
            maps.get("AcropolisLE"),
            [bot, Computer(Race.Random, Difficulty.Easy)],
            realtime=False,
        )
        print(f"Game result: {result}")
