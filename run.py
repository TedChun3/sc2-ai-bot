import sys

from bot import DIFFICULTY_MAP, ProtossBot
from ladder import run_ladder_game
from sc2 import maps
from sc2.data import Race
from sc2.main import run_game
from sc2.player import Bot, Computer


def make_bot():
    return Bot(Race.Protoss, ProtossBot())


if __name__ == "__main__":
    bot = make_bot()

    if "--LadderServer" in sys.argv:
        result, opponent_id = run_ladder_game(bot)
        print(f"{result} against opponent {opponent_id}")
    else:
        result = run_game(
            maps.get("AcropolisLE"),
            [
                bot,
                Computer(Race.Random, DIFFICULTY_MAP["medium"]),
            ],
            realtime=False,
        )
        print(f"Game result: {result}")
