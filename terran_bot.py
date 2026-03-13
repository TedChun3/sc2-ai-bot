"""
Terran Bot - Reaper Opening → Marine/Marauder Bio
"""

from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2 import maps


class TerranBot(BotAI):
    def __init__(self):
        super().__init__()
        self.attack_triggered = False

    async def on_step(self, iteration: int):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_supply()
        await self.build_gas()
        await self.build_barracks()
        await self.build_factory_starport()
        await self.train_army()
        await self.manage_orbital()
        await self.attack()

    async def build_workers(self):
        for cc in self.townhalls.ready:
            if (
                self.can_afford(UnitTypeId.SCV)
                and cc.is_idle
                and self.workers.amount < self.townhalls.amount * 22
            ):
                cc.train(UnitTypeId.SCV)

    async def build_supply(self):
        if (
            self.supply_left < 5
            and not self.already_pending(UnitTypeId.SUPPLYDEPOT)
            and self.can_afford(UnitTypeId.SUPPLYDEPOT)
        ):
            await self.build(
                UnitTypeId.SUPPLYDEPOT,
                near=self.townhalls.ready.random.position.towards(
                    self.game_info.map_center, 5
                ),
            )

        # Lower completed supply depots
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

    async def build_gas(self):
        if self.structures(UnitTypeId.BARRACKS).amount > 0:
            for cc in self.townhalls.ready:
                geysers = self.vespene_geyser.closer_than(15, cc)
                for geyser in geysers:
                    if not self.can_afford(UnitTypeId.REFINERY):
                        break
                    if not self.gas_buildings.closer_than(1, geyser):
                        await self.build(UnitTypeId.REFINERY, geyser)

    async def build_barracks(self):
        if (
            self.structures(UnitTypeId.SUPPLYDEPOT).ready
            or self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready
        ):
            if (
                self.structures(UnitTypeId.BARRACKS).amount < 3
                and self.can_afford(UnitTypeId.BARRACKS)
                and not self.already_pending(UnitTypeId.BARRACKS)
            ):
                await self.build(
                    UnitTypeId.BARRACKS,
                    near=self.townhalls.ready.random.position.towards(
                        self.game_info.map_center, 8
                    ),
                )

            # Add Tech Lab for Marauders
            for rax in self.structures(UnitTypeId.BARRACKS).ready:
                if not rax.has_add_on and rax.is_idle:
                    if self.can_afford(UnitTypeId.BARRACKSTECHLAB):
                        rax.build(UnitTypeId.BARRACKSTECHLAB)

    async def build_factory_starport(self):
        """Build Factory (for Starport) → Starport (for Medivacs)."""
        if not self.structures(UnitTypeId.BARRACKS).ready:
            return

        if (
            not self.structures(UnitTypeId.FACTORY)
            and not self.already_pending(UnitTypeId.FACTORY)
            and self.can_afford(UnitTypeId.FACTORY)
        ):
            await self.build(
                UnitTypeId.FACTORY,
                near=self.townhalls.ready.random.position.towards(
                    self.game_info.map_center, 8
                ),
            )

        if (
            self.structures(UnitTypeId.FACTORY).ready
            and not self.structures(UnitTypeId.STARPORT)
            and not self.already_pending(UnitTypeId.STARPORT)
            and self.can_afford(UnitTypeId.STARPORT)
        ):
            await self.build(
                UnitTypeId.STARPORT,
                near=self.townhalls.ready.random.position.towards(
                    self.game_info.map_center, 8
                ),
            )

    async def manage_orbital(self):
        """Upgrade CC to Orbital, use MULE."""
        for cc in self.townhalls(UnitTypeId.COMMANDCENTER).ready.idle:
            if self.can_afford(UnitTypeId.ORBITALCOMMAND):
                cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).ready:
            if oc.energy >= 50:
                mfs = self.mineral_field.closer_than(15, oc)
                if mfs:
                    oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mfs.random)

    async def train_army(self):
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            if rax.is_idle:
                if (
                    rax.has_add_on
                    and self.can_afford(UnitTypeId.MARAUDER)
                    and self.supply_left >= 2
                ):
                    rax.train(UnitTypeId.MARAUDER)
                elif self.can_afford(UnitTypeId.MARINE) and self.supply_left >= 1:
                    rax.train(UnitTypeId.MARINE)

        # Medivacs
        for sp in self.structures(UnitTypeId.STARPORT).ready.idle:
            if self.can_afford(UnitTypeId.MEDIVAC) and self.supply_left >= 2:
                sp.train(UnitTypeId.MEDIVAC)

    async def attack(self):
        army = self.units.of_type(
            {UnitTypeId.MARINE, UnitTypeId.MARAUDER, UnitTypeId.MEDIVAC}
        )

        if army.amount >= 20:
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
            Bot(Race.Terran, TerranBot()),
            Computer(Race.Zerg, Difficulty.Medium),
        ],
        realtime=False,
    )
