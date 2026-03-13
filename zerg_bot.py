"""
Zerg Bot - Hatchery First → Zergling/Roach
"""

from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2 import maps


class ZergBot(BotAI):
    def __init__(self):
        super().__init__()
        self.attack_triggered = False

    async def on_step(self, iteration: int):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_overlords()
        await self.expand()
        await self.build_gas()
        await self.build_spawning_pool()
        await self.build_roach_warren()
        await self.inject_larvae()
        await self.train_army()
        await self.attack()

    async def build_workers(self):
        for hatch in self.townhalls.ready:
            if (
                self.can_afford(UnitTypeId.DRONE)
                and self.supply_left >= 1
                and self.workers.amount < self.townhalls.amount * 16
                and hatch.is_idle
            ):
                hatch.train(UnitTypeId.DRONE)

    async def build_overlords(self):
        if (
            self.supply_left < 4
            and not self.already_pending(UnitTypeId.OVERLORD)
            and self.can_afford(UnitTypeId.OVERLORD)
        ):
            self.townhalls.ready.random.train(UnitTypeId.OVERLORD)

    async def expand(self):
        if (
            self.townhalls.amount < 3
            and self.can_afford(UnitTypeId.HATCHERY)
            and not self.already_pending(UnitTypeId.HATCHERY)
        ):
            await self.expand_now()

    async def build_gas(self):
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready:
            for hatch in self.townhalls.ready:
                geysers = self.vespene_geyser.closer_than(15, hatch)
                for geyser in geysers:
                    if not self.can_afford(UnitTypeId.EXTRACTOR):
                        break
                    if not self.gas_buildings.closer_than(1, geyser):
                        await self.build(UnitTypeId.EXTRACTOR, geyser)

    async def build_spawning_pool(self):
        if (
            not self.structures(UnitTypeId.SPAWNINGPOOL)
            and not self.already_pending(UnitTypeId.SPAWNINGPOOL)
            and self.can_afford(UnitTypeId.SPAWNINGPOOL)
        ):
            await self.build(
                UnitTypeId.SPAWNINGPOOL,
                near=self.townhalls.ready.random.position.towards(
                    self.game_info.map_center, 5
                ),
            )

    async def build_roach_warren(self):
        if (
            self.structures(UnitTypeId.SPAWNINGPOOL).ready
            and not self.structures(UnitTypeId.ROACHWARREN)
            and not self.already_pending(UnitTypeId.ROACHWARREN)
            and self.can_afford(UnitTypeId.ROACHWARREN)
        ):
            await self.build(
                UnitTypeId.ROACHWARREN,
                near=self.townhalls.ready.random.position.towards(
                    self.game_info.map_center, 5
                ),
            )

    async def inject_larvae(self):
        for queen in self.units(UnitTypeId.QUEEN).idle:
            for hatch in self.townhalls.ready:
                if queen.energy >= 25:
                    queen(AbilityId.EFFECT_INJECTLARVA, hatch)
                    break

    async def train_army(self):
        if not self.structures(UnitTypeId.SPAWNINGPOOL).ready:
            return

        # Train queens (1 per hatch)
        if (
            self.units(UnitTypeId.QUEEN).amount < self.townhalls.amount
            and self.can_afford(UnitTypeId.QUEEN)
        ):
            for hatch in self.townhalls.ready.idle:
                if self.can_afford(UnitTypeId.QUEEN):
                    hatch.train(UnitTypeId.QUEEN)
                    break

        # Train roaches if warren ready, otherwise zerglings
        for larva in self.units(UnitTypeId.LARVA):
            if (
                self.structures(UnitTypeId.ROACHWARREN).ready
                and self.can_afford(UnitTypeId.ROACH)
                and self.supply_left >= 2
            ):
                larva.train(UnitTypeId.ROACH)
            elif self.can_afford(UnitTypeId.ZERGLING) and self.supply_left >= 1:
                larva.train(UnitTypeId.ZERGLING)

    async def attack(self):
        army = self.units.of_type({UnitTypeId.ZERGLING, UnitTypeId.ROACH})

        if army.amount >= 25:
            self.attack_triggered = True

        if self.attack_triggered and army.amount > 0:
            target = self.enemy_start_locations[0]
            for unit in army:
                unit.attack(target)
        elif army.amount > 0:
            rally = self.townhalls.ready.center.towards(
                self.game_info.map_center, 10
            )
            for unit in army.idle:
                unit.attack(rally)


if __name__ == "__main__":
    run_game(
        maps.get("Simple64"),
        [
            Bot(Race.Zerg, ZergBot()),
            Computer(Race.Protoss, Difficulty.Medium),
        ],
        realtime=False,
    )
