"""
Protoss Bot - 2-Gate Zealot Rush → Stalker Transition
"""

import argparse
import sys

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point2

DIFFICULTY_MAP = {
    "easy": Difficulty.Easy,
    "medium": Difficulty.Medium,
    "hard": Difficulty.Hard,
    "harder": Difficulty.Harder,
    "veryhard": Difficulty.VeryHard,
    "elite": Difficulty.CheatVision,
}


class ProtossBot(BotAI):
    """
    Simple Protoss bot:
    1. Build workers up to 22 per base
    2. Build 2 Gateways
    3. Get Cybernetics Core
    4. Mass Zealots early, transition to Stalkers
    5. Attack when army is big enough
    """

    def __init__(self):
        super().__init__()
        self.attack_triggered = False
        self.proxy_built = False

    async def on_step(self, iteration: int):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_gateways()
        await self.build_gas()
        await self.build_cyber_core()
        await self.train_army()
        await self.chrono_boost()
        await self.attack()

    async def build_workers(self):
        """Build probes up to 22 per nexus."""
        for nexus in self.townhalls.ready:
            if self.can_afford(UnitTypeId.PROBE) and nexus.is_idle:
                if self.workers.amount < self.townhalls.amount * 22:
                    nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self):
        """Build pylons when supply is getting low."""
        if self.supply_left < 5 and not self.already_pending(UnitTypeId.PYLON):
            if self.can_afford(UnitTypeId.PYLON):
                await self.build(
                    UnitTypeId.PYLON,
                    near=self.townhalls.ready.random.position.towards(
                        self.game_info.map_center, 5
                    ),
                )

    async def build_gateways(self):
        """Build up to 3 gateways."""
        if (
            self.structures(UnitTypeId.PYLON).ready
            and self.structures(UnitTypeId.GATEWAY).amount < 3
            and self.can_afford(UnitTypeId.GATEWAY)
            and not self.already_pending(UnitTypeId.GATEWAY)
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            await self.build(UnitTypeId.GATEWAY, near=pylon)

    async def build_gas(self):
        """Build assimilators on geysers near nexus."""
        if self.structures(UnitTypeId.GATEWAY).ready:
            for nexus in self.townhalls.ready:
                geysers = self.vespene_geyser.closer_than(15, nexus)
                for geyser in geysers:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break
                    if not self.gas_buildings.closer_than(1, geyser):
                        await self.build(UnitTypeId.ASSIMILATOR, geyser)

    async def build_cyber_core(self):
        """Build Cybernetics Core after first Gateway."""
        if (
            self.structures(UnitTypeId.GATEWAY).ready
            and not self.structures(UnitTypeId.CYBERNETICSCORE)
            and not self.already_pending(UnitTypeId.CYBERNETICSCORE)
            and self.can_afford(UnitTypeId.CYBERNETICSCORE)
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)

    async def train_army(self):
        """Train Zealots and Stalkers from Gateways."""
        for gw in self.structures(UnitTypeId.GATEWAY).ready:
            if gw.is_idle:
                if (
                    self.structures(UnitTypeId.CYBERNETICSCORE).ready
                    and self.can_afford(UnitTypeId.STALKER)
                    and self.supply_left >= 2
                ):
                    gw.train(UnitTypeId.STALKER)
                elif self.can_afford(UnitTypeId.ZEALOT) and self.supply_left >= 2:
                    gw.train(UnitTypeId.ZEALOT)

    async def chrono_boost(self):
        """Chrono boost gateways producing units."""
        for nexus in self.townhalls.ready:
            if nexus.energy >= 50:
                for gw in self.structures(UnitTypeId.GATEWAY).ready:
                    if not gw.is_idle and not gw.has_buff(
                        AbilityId.EFFECT_CHRONOBOOSTENERGYCOST
                    ):
                        nexus(
                            AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, gw
                        )
                        break

    async def attack(self):
        """Attack when we have enough army supply."""
        army = self.units.of_type(
            {UnitTypeId.ZEALOT, UnitTypeId.STALKER}
        )
        if army.amount >= 15 or (self.supply_used >= 100):
            self.attack_triggered = True

        if self.attack_triggered and army.amount > 0:
            target = self.enemy_start_locations[0]
            for unit in army:
                unit.attack(target)
        elif army.amount > 0:
            # Rally near natural expansion
            rally = self.townhalls.ready.center.towards(
                self.game_info.map_center, 10
            )
            for unit in army.idle:
                unit.attack(rally)


def main():
    parser = argparse.ArgumentParser(description="SC2 Protoss AI Bot")
    parser.add_argument(
        "--difficulty",
        type=str,
        default="medium",
        choices=list(DIFFICULTY_MAP.keys()),
        help="Computer difficulty",
    )
    parser.add_argument(
        "--race",
        type=str,
        default="protoss",
        choices=["protoss", "terran", "zerg", "random"],
        help="Bot race",
    )
    parser.add_argument(
        "--map",
        type=str,
        default="Simple64",
        help="Map name",
    )
    parser.add_argument(
        "--save-replay",
        action="store_true",
        help="Save replay after game",
    )
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Run in real-time (slower)",
    )

    args = parser.parse_args()

    enemy_race = {
        "protoss": Race.Protoss,
        "terran": Race.Terran,
        "zerg": Race.Zerg,
        "random": Race.Random,
    }

    result = run_game(
        maps.get(args.map),
        [
            Bot(Race.Protoss, ProtossBot()),
            Computer(
                enemy_race.get(args.race, Race.Random),
                DIFFICULTY_MAP[args.difficulty],
            ),
        ],
        realtime=args.realtime,
        save_replay_as="replay.SC2Replay" if args.save_replay else None,
    )
    print(f"Game result: {result}")


if __name__ == "__main__":
    main()
