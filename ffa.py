"""
Free-For-All: 3 bots fight each other!
Usage: python3.12 ffa.py [--map MAP] [--realtime]
"""

import argparse

from sc2 import maps
from sc2.data import Race
from sc2.main import run_game
from sc2.player import Bot

from bot import ProtossBot
from zerg_bot import ZergBot
from terran_bot import TerranBot


def main():
    parser = argparse.ArgumentParser(description="SC2 3-Bot FFA")
    parser.add_argument("--map", type=str, default="Simple128", help="Map name")
    parser.add_argument("--realtime", action="store_true", help="Real-time speed")
    parser.add_argument("--save-replay", action="store_true", help="Save replay")
    args = parser.parse_args()

    result = run_game(
        maps.get(args.map),
        [
            Bot(Race.Protoss, ProtossBot()),
            Bot(Race.Zerg, ZergBot()),
            Bot(Race.Terran, TerranBot()),
        ],
        realtime=args.realtime,
        save_replay_as="ffa_replay.SC2Replay" if args.save_replay else None,
    )
    print(f"Game result: {result}")


if __name__ == "__main__":
    main()
