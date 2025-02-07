from __future__ import annotations
import warnings
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING

from .cache import property_immutable_cache, property_mutable_cache
from .constants import (
    transforming,
    IS_STRUCTURE,
    IS_LIGHT,
    IS_ARMORED,
    IS_BIOLOGICAL,
    IS_MECHANICAL,
    IS_MASSIVE,
    IS_PSIONIC,
    UNIT_BATTLECRUISER,
    UNIT_ORACLE,
    TARGET_GROUND,
    TARGET_AIR,
    TARGET_BOTH,
    IS_SNAPSHOT,
    IS_VISIBLE,
    IS_MINE,
    IS_ENEMY,
    IS_CLOAKED,
    IS_REVEALED,
    CAN_BE_ATTACKED,
    IS_CARRYING_MINERALS,
    IS_CARRYING_VESPENE,
    IS_CARRYING_RESOURCES,
    IS_ATTACKING,
    IS_PATROLLING,
    IS_GATHERING,
    IS_RETURNING,
    IS_COLLECTING,
    IS_CONSTRUCTING_SCV,
    IS_REPAIRING,
    IS_DETECTOR,
    UNIT_PHOTONCANNON,
    UNIT_COLOSSUS,
)
from .data import (
    Alliance,
    Attribute,
    CloakState,
    DisplayType,
    Race,
    TargetType,
    warpgate_abilities,
    TargetType,
    Target,
    race_gas,
)
from .ids.ability_id import AbilityId
from .ids.buff_id import BuffId
from .ids.upgrade_id import UpgradeId
from .ids.unit_typeid import UnitTypeId
from .position import Point2, Point3
from .unit_command import UnitCommand

warnings.simplefilter("once")

if TYPE_CHECKING:
    from .bot_ai import BotAI
    from .game_data import AbilityData


class UnitOrder:
    @classmethod
    def from_proto(cls, proto, bot_object: BotAI):
        return cls(
            bot_object._game_data.abilities[proto.ability_id],
            (proto.target_world_space_pos if proto.HasField("target_world_space_pos") else proto.target_unit_tag),
            proto.progress,
        )

    def __init__(self, ability: AbilityData, target, progress: float = None):
        """
        :param ability:
        :param target:
        :param progress:
        """
        self.ability = ability
        self.target = target
        self.progress = progress

    def __repr__(self) -> str:
        return f"UnitOrder({self.ability}, {self.target}, {self.progress})"


class Unit:
    def __init__(self, proto_data, bot_object: BotAI):
        """
        :param proto_data:
        :param bot_object:
        """
        self._proto = proto_data
        self._bot_object = bot_object
        # Used by property_immutable_cache
        self.cache = {}

    def __repr__(self) -> str:
        """ Returns string of this form: Unit(name='SCV', tag=4396941328). """
        return f"Unit(name={self.name !r}, tag={self.tag})"

    @property_immutable_cache
    def type_id(self) -> UnitTypeId:
        """ UnitTypeId found in sc2/ids/unit_typeid.
        Caches all type_ids of the same unit type. """
        unit_type = self._proto.unit_type
        if unit_type not in self._bot_object._game_data.unit_types:
            self._bot_object._game_data.unit_types[unit_type] = UnitTypeId(unit_type)
        return self._bot_object._game_data.unit_types[unit_type]

    @property_immutable_cache
    def _type_data(self) -> "UnitTypeData":
        """ Provides the unit type data. """
        return self._bot_object._game_data.units[self._proto.unit_type]

    @property
    def name(self) -> str:
        """ Returns the name of the unit. """
        return self._type_data.name

    @property
    def race(self) -> Race:
        """ Returns the race of the unit """
        return Race(self._type_data._proto.race)

    @property
    def tag(self) -> int:
        """ Returns the unique tag of the unit. """
        return self._proto.tag

    @property
    def is_structure(self) -> bool:
        """ Checks if the unit is a structure. """
        return IS_STRUCTURE in self._type_data.attributes

    @property
    def is_light(self) -> bool:
        """ Checks if the unit has the 'light' attribute. """
        return IS_LIGHT in self._type_data.attributes

    @property
    def is_armored(self) -> bool:
        """ Checks if the unit has the 'armored' attribute. """
        return IS_ARMORED in self._type_data.attributes

    @property
    def is_biological(self) -> bool:
        """ Checks if the unit has the 'biological' attribute. """
        return IS_BIOLOGICAL in self._type_data.attributes

    @property
    def is_mechanical(self) -> bool:
        """ Checks if the unit has the 'mechanical' attribute. """
        return IS_MECHANICAL in self._type_data.attributes

    @property
    def is_massive(self) -> bool:
        """ Checks if the unit has the 'massive' attribute. """
        return IS_MASSIVE in self._type_data.attributes

    @property
    def is_psionic(self) -> bool:
        """ Checks if the unit has the 'psionic' attribute. """
        return IS_PSIONIC in self._type_data.attributes

    @property
    def tech_alias(self) -> Optional[List[UnitTypeId]]:
        """ Building tech equality, e.g. OrbitalCommand is the same as CommandCenter
        For Hive, this returns [UnitTypeId.Hatchery, UnitTypeId.Lair]
        For SCV, this returns None """
        return self._type_data.tech_alias

    @property
    def unit_alias(self) -> Optional[UnitTypeId]:
        """ Building type equality, e.g. FlyingOrbitalCommand is the same as OrbitalCommand
        For flying OrbitalCommand, this returns UnitTypeId.OrbitalCommand
        For SCV, this returns None """
        return self._type_data.unit_alias

    @property_immutable_cache
    def _weapons(self):
        """ Returns the weapons of the unit. """
        try:
            return self._type_data._proto.weapons
        except:
            return None

    @property_immutable_cache
    def can_attack(self) -> bool:
        """ Checks if the unit can attack at all. """
        # TODO BATTLECRUISER doesnt have weapons in proto?!
        return bool(self._weapons) or self.type_id in {UNIT_BATTLECRUISER, UNIT_ORACLE}

    @property_immutable_cache
    def can_attack_both(self) -> bool:
        """ Checks if the unit can attack both ground and air units. """
        if self.type_id == UNIT_BATTLECRUISER:
            return True
        if self._weapons:
            return any(weapon.type in TARGET_BOTH for weapon in self._weapons)
        return False

    @property_immutable_cache
    def can_attack_ground(self) -> bool:
        """ Checks if the unit can attack ground units. """
        if self.type_id in {UNIT_BATTLECRUISER, UNIT_ORACLE}:
            return True
        if self._weapons:
            return any(weapon.type in TARGET_GROUND for weapon in self._weapons)
        return False

    @property_immutable_cache
    def ground_dps(self) -> Union[int, float]:
        """ Returns the dps against ground units. Does not include upgrades. """
        if self.can_attack_ground:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_GROUND), None)
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @property_immutable_cache
    def ground_range(self) -> Union[int, float]:
        """ Returns the range against ground units. Does not include upgrades. """
        if self.type_id == UNIT_ORACLE:
            return 4
        if self.type_id == UNIT_BATTLECRUISER:
            return 6
        if self.can_attack_ground:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_GROUND), None)
            if weapon:
                return weapon.range
        return 0

    @property_immutable_cache
    def can_attack_air(self) -> bool:
        """ Checks if the unit can air attack at all. Does not include upgrades. """
        if self.type_id == UNIT_BATTLECRUISER:
            return True
        if self._weapons:
            return any(weapon.type in TARGET_AIR for weapon in self._weapons)
        return False

    @property_immutable_cache
    def air_dps(self) -> Union[int, float]:
        """ Returns the dps against air units. Does not include upgrades. """
        if self.can_attack_air:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_AIR), None)
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @property_immutable_cache
    def air_range(self) -> Union[int, float]:
        """ Returns the range against air units. Does not include upgrades. """
        if self.type_id == UNIT_BATTLECRUISER:
            return 6
        if self.can_attack_air:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_AIR), None)
            if weapon:
                return weapon.range
        return 0

    @property_immutable_cache
    def bonus_damage(self):
        """ Returns a tuple of form '(bonus damage, armor type)' if unit does 'bonus damage' against 'armor type'.
        Possible armor typs are: 'Light', 'Armored', 'Biological', 'Mechanical', 'Psionic', 'Massive', 'Structure'. """
        # TODO: Consider units with ability attacks (Oracle, Baneling) or multiple attacks (Thor).
        if self._weapons:
            for weapon in self._weapons:
                if weapon.damage_bonus:
                    b = weapon.damage_bonus[0]
                    return (b.bonus, Attribute(b.attribute).name)
        else:
            return None

    @property
    def armor(self) -> Union[int, float]:
        """ Returns the armor of the unit. Does not include upgrades """
        return self._type_data._proto.armor

    @property
    def sight_range(self) -> Union[int, float]:
        """ Returns the sight range of the unit. """
        return self._type_data._proto.sight_range

    @property
    def movement_speed(self) -> Union[int, float]:
        """ Returns the movement speed of the unit. Does not include upgrades or buffs. """
        return self._type_data._proto.movement_speed

    @property
    def is_mineral_field(self) -> bool:
        """ Checks if the unit is a mineral field. """
        return self._type_data.has_minerals

    @property
    def is_vespene_geyser(self) -> bool:
        """ Checks if the unit is a non-empty vespene geyser or gas extraction building. """
        return self._type_data.has_vespene

    @property
    def health(self) -> Union[int, float]:
        """ Returns the health of the unit. Does not include shields. """
        return self._proto.health

    @property
    def health_max(self) -> Union[int, float]:
        """ Returns the maximum health of the unit. Does not include shields. """
        return self._proto.health_max

    @property
    def health_percentage(self) -> Union[int, float]:
        """ Returns the percentage of health the unit has. Does not include shields. """
        if self._proto.health_max == 0:
            return 0
        return self._proto.health / self._proto.health_max

    @property
    def shield(self) -> Union[int, float]:
        """ Returns the shield points the unit has. Returns 0 for non-protoss units. """
        return self._proto.shield

    @property
    def shield_max(self) -> Union[int, float]:
        """ Returns the maximum shield points the unit can have. Returns 0 for non-protoss units. """
        return self._proto.shield_max

    @property
    def shield_percentage(self) -> Union[int, float]:
        """ Returns the percentage of shield points the unit has. Returns 0 for non-protoss units. """
        if self._proto.shield_max == 0:
            return 0
        return self._proto.shield / self._proto.shield_max

    @property
    def energy(self) -> Union[int, float]:
        """ Returns the amount of energy the unit has. Returns 0 for units without energy. """
        return self._proto.energy

    @property
    def energy_max(self) -> Union[int, float]:
        """ Returns the maximum amount of energy the unit can have. Returns 0 for units without energy. """
        return self._proto.energy_max

    @property
    def energy_percentage(self) -> Union[int, float]:
        """ Returns the percentage of amount of energy the unit has. Returns 0 for units without energy. """
        if self._proto.energy_max == 0:
            return 0
        return self._proto.energy / self._proto.energy_max

    @property
    def is_snapshot(self) -> bool:
        """ Checks if the unit is only available as a snapshot for the bot.
        Enemy buildings that have been scouted and are in the fog of war or
        attacking enemy units on higher, not visible ground appear this way. """
        return self._proto.display_type == IS_SNAPSHOT

    @property
    def is_visible(self) -> bool:
        """ Checks if the unit is visible for the bot.
        NOTE: This means the bot has vision of the position of the unit!
        It does not give any information about the cloak status of the unit."""
        return self._proto.display_type == IS_VISIBLE

    @property
    def alliance(self) -> Alliance:
        """ Returns the team the unit belongs to. """
        return self._proto.alliance

    @property
    def is_mine(self) -> bool:
        """ Checks if the unit is controlled by the bot. """
        return self._proto.alliance == IS_MINE

    @property
    def is_enemy(self) -> bool:
        """ Checks if the unit is hostile. """
        return self._proto.alliance == IS_ENEMY

    @property
    def owner_id(self) -> int:
        """ Returns the owner of the unit. This is a value of 1 or 2 in a two player game. """
        return self._proto.owner

    @property
    def position_tuple(self) -> Tuple[float, float]:
        """ Returns the 2d position of the unit as tuple without conversion to Point2. """
        return self._proto.pos.x, self._proto.pos.y

    @property_immutable_cache
    def position(self) -> Point2:
        """ Returns the 2d position of the unit. """
        return Point2.from_proto(self._proto.pos)

    @property_immutable_cache
    def position3d(self) -> Point3:
        """ Returns the 3d position of the unit. """
        return Point3.from_proto(self._proto.pos)

    def distance_to(self, p: Union[Unit, Point2, Point3]) -> Union[int, float]:
        """ Using the 2d distance between self and p.
        To calculate the 3d distance, use unit.position3d.distance_to(p)

        :param p: """
        if isinstance(p, Unit):
            return self._bot_object._distance_squared_unit_to_unit(self, p) ** 0.5
        return self._bot_object.distance_math_hypot(self.position_tuple, p)

    def target_in_range(self, target: Unit, bonus_distance: Union[int, float] = 0) -> bool:
        """ Checks if the target is in range.
        Includes the target's radius when calculating distance to target.

        :param target:
        :param bonus_distance: """
        # TODO: Fix this because immovable units (sieged tank, planetary fortress etc.) have a little lower range than this formula
        if self.can_attack_ground and not target.is_flying:
            unit_attack_range = self.ground_range
        elif self.can_attack_air and (target.is_flying or target.type_id == UNIT_COLOSSUS):
            unit_attack_range = self.air_range
        else:
            return False
        return (
            self._bot_object._distance_squared_unit_to_unit(self, target)
            <= (self.radius + target.radius + unit_attack_range + bonus_distance) ** 2
        )

    def in_ability_cast_range(
        self, ability_id: AbilityId, target: Union[Unit, Point2], bonus_distance: float = 0
    ) -> bool:
        """ Test if a unit is able to cast an ability on the target without checking ability cooldown (like stalker blink) or if ability is made available through research (like HT storm).

        :param ability_id:
        :param target:
        :param bonus_distance: """
        cast_range = self._bot_object._game_data.abilities[ability_id.value]._proto.cast_range
        assert cast_range > 0, f"Checking for an ability ({ability_id}) that has no cast range"
        ability_target_type = self._bot_object._game_data.abilities[ability_id.value]._proto.target
        # For casting abilities that target other units, like transfuse, feedback, snipe, yamato
        if ability_target_type in {Target.Unit.value, Target.PointOrUnit.value} and isinstance(target, Unit):
            return (
                self._bot_object._distance_squared_unit_to_unit(self, target)
                <= (cast_range + self.radius + target.radius + bonus_distance) ** 2
            )
        # For casting abilities on the ground, like queen creep tumor, ravager bile, HT storm
        if ability_target_type in {Target.Point.value, Target.PointOrUnit.value} and isinstance(
            target, (Point2, tuple)
        ):
            return (
                self._bot_object._distance_pos_to_pos(self.position_tuple, target)
                <= cast_range + self.radius + bonus_distance
            )
        return False

    @property
    def facing(self) -> Union[int, float]:
        """ Returns direction the unit is facing as a float in range [0,2π). 0 is in direction of x axis."""
        return self._proto.facing

    def is_facing(self, other_unit: Unit, angle_error: float = 0.05) -> bool:
        """ Check if this unit is facing the target unit. If you make angle_error too small, there might be rounding errors. If you make angle_error too big, this function might return false positives.

        :param other_unit:
        :param angle_error: """
        angle = math.atan2(
            other_unit.position_tuple[1] - self.position_tuple[1], other_unit.position_tuple[0] - self.position_tuple[0]
        )
        if angle < 0:
            angle += math.pi * 2
        angle_difference = math.fabs(angle - self.facing)
        return angle_difference < angle_error

    @property
    def radius(self) -> Union[int, float]:
        """ Half of unit size. See https://liquipedia.net/starcraft2/Unit_Statistics_(Legacy_of_the_Void) """
        return self._proto.radius

    @property
    def build_progress(self) -> Union[int, float]:
        """ Returns completion in range [0,1]."""
        return self._proto.build_progress

    @property
    def is_ready(self) -> bool:
        """ Checks if the unit is completed. """
        return self.build_progress == 1

    @property
    def cloak(self) -> CloakState:
        """ Returns cloak state.
        See https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_unit.h#L95 """
        return self._proto.cloak

    @property
    def is_cloaked(self) -> bool:
        """ Checks if the unit is cloaked. """
        return self._proto.cloak in IS_CLOAKED

    @property
    def is_revealed(self) -> bool:
        """ Checks if the unit is revealed. """
        return self._proto.cloak is IS_REVEALED

    @property
    def can_be_attacked(self) -> bool:
        """ Checks if the unit is revealed or not cloaked and therefore can be attacked. """
        return self._proto.cloak in CAN_BE_ATTACKED

    @property_immutable_cache
    def buffs(self) -> Set:
        """ Returns the set of current buffs the unit has. """
        return {BuffId(buff_id) for buff_id in self._proto.buff_ids}

    @property_immutable_cache
    def is_carrying_minerals(self) -> bool:
        """ Checks if a worker or MULE is carrying (gold-)minerals. """
        return not IS_CARRYING_MINERALS.isdisjoint(self.buffs)

    @property_immutable_cache
    def is_carrying_vespene(self) -> bool:
        """ Checks if a worker is carrying vespene gas. """
        return not IS_CARRYING_VESPENE.isdisjoint(self.buffs)

    @property_immutable_cache
    def is_carrying_resource(self) -> bool:
        """ Checks if a worker is carrying a resource. """
        return not IS_CARRYING_RESOURCES.isdisjoint(self.buffs)

    @property
    def detect_range(self) -> Union[int, float]:
        """ Returns the detection distance of the unit. """
        return self._proto.detect_range

    @property_immutable_cache
    def is_detector(self) -> bool:
        """ Checks if the unit is a detector. Has to be completed
        in order to detect and Photoncannons also need to be powered. """
        return self.is_ready and (self.type_id in IS_DETECTOR or self.type_id == UNIT_PHOTONCANNON and self.is_powered)

    @property
    def radar_range(self) -> Union[int, float]:
        return self._proto.radar_range

    @property
    def is_selected(self) -> bool:
        """ Checks if the unit is currently selected. """
        return self._proto.is_selected

    @property
    def is_on_screen(self) -> bool:
        """ Checks if the unit is on the screen. """
        return self._proto.is_on_screen

    @property
    def is_blip(self) -> bool:
        """ Checks if the unit is detected by a sensor tower. """
        return self._proto.is_blip

    @property
    def is_powered(self) -> bool:
        """ Checks if the unit is powered by a pylon or warppism. """
        return self._proto.is_powered

    @property
    def is_active(self) -> bool:
        """ Checks if the unit is currently training or researching. """
        return self._proto.is_active

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR SNAPSHOTS

    @property
    def mineral_contents(self) -> int:
        """ Returns the amount of minerals remaining in a mineral field. """
        return self._proto.mineral_contents

    @property
    def vespene_contents(self) -> int:
        """ Returns the amount of gas remaining in a geyser. """
        return self._proto.vespene_contents

    @property
    def has_vespene(self) -> bool:
        """ Checks if a geyser has any gas remaining.
        You can't build extractors on empty geysers. """
        return bool(self._proto.vespene_contents)

    @property
    def is_flying(self) -> bool:
        """ Checks if the unit is flying. """
        return self._proto.is_flying or self.has_buff(BuffId.GRAVITONBEAM)

    @property
    def is_burrowed(self) -> bool:
        """ Checks if the unit is burrowed. """
        return self._proto.is_burrowed

    @property
    def is_hallucination(self) -> bool:
        """ Returns True if the unit is your own hallucination or detected. """
        return self._proto.is_hallucination

    @property
    def attack_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units attack.
        # NOTE: Returns 0 for units without a weapon. """
        return self._proto.attack_upgrade_level

    @property
    def armor_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units armor. """
        return self._proto.armor_upgrade_level

    @property
    def shield_upgrade_level(self) -> int:
        """ Returns the upgrade level of the units shield.
        # NOTE: Returns 0 for units without a shield. """
        return self._proto.shield_upgrade_level

    @property
    def buff_duration_remain(self) -> int:
        """ Returns the amount of remaining frames of the visible timer bar.
        # NOTE: Returns 0 for units without a timer bar. """
        return self._proto.buff_duration_remain

    @property
    def buff_duration_max(self) -> int:
        """ Returns the maximum amount of frames of the visible timer bar.
        # NOTE: Returns 0 for units without a timer bar. """
        return self._proto.buff_duration_max

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR ENEMIES

    @property_mutable_cache
    def orders(self) -> List[UnitOrder]:
        """ Returns the a list of the current orders. """
        return [UnitOrder.from_proto(order, self._bot_object) for order in self._proto.orders]

    @property_immutable_cache
    def order_target(self) -> Optional[Union[int, Point2]]:
        """ Returns the target tag (if it is a Unit) or Point2 (if it is a Position)
        from the first order, returns None if the unit is idle """
        if self.orders:
            target = self.orders[0].target
            if isinstance(target, int):
                return target
            else:
                return Point2.from_proto(target)
        return None

    @property
    def noqueue(self) -> bool:
        """ Checks if the unit is idle. """
        warnings.warn("noqueue will be removed soon, please use is_idle instead", DeprecationWarning, stacklevel=2)
        return self.is_idle

    @property
    def is_idle(self) -> bool:
        """ Checks if unit is idle. """
        return not self._proto.orders

    def is_using_ability(self, abilities: Union[AbilityId, Set[AbilityId]]) -> bool:
        """ Check if the unit is using one of the given abilities.
        Only works for own units. """
        if not self.orders:
            return False
        if isinstance(abilities, AbilityId):
            abilities = {abilities}
        return self.orders[0].ability.id in abilities

    @property_immutable_cache
    def is_moving(self) -> bool:
        """ Checks if the unit is moving.
        Only works for own units. """
        return self.is_using_ability(AbilityId.MOVE)

    @property_immutable_cache
    def is_attacking(self) -> bool:
        """ Checks if the unit is attacking.
        Only works for own units. """
        return self.is_using_ability(IS_ATTACKING)

    @property_immutable_cache
    def is_patrolling(self) -> bool:
        """ Checks if a unit is patrolling.
        Only works for own units. """
        return self.is_using_ability(IS_PATROLLING)

    @property_immutable_cache
    def is_gathering(self) -> bool:
        """ Checks if a unit is on its way to a mineral field or vespene geyser to mine.
        Only works for own units. """
        return self.is_using_ability(IS_GATHERING)

    @property_immutable_cache
    def is_returning(self) -> bool:
        """ Checks if a unit is returning from mineral field or vespene geyser to deliver resources to townhall.
        Only works for own units. """
        return self.is_using_ability(IS_RETURNING)

    @property_immutable_cache
    def is_collecting(self) -> bool:
        """ Checks if a unit is gathering or returning.
        Only works for own units. """
        return self.is_using_ability(IS_COLLECTING)

    @property_immutable_cache
    def is_constructing_scv(self) -> bool:
        """ Checks if the unit is an SCV that is currently building.
        Only works for own units. """
        return self.is_using_ability(IS_CONSTRUCTING_SCV)

    @property_immutable_cache
    def is_transforming(self) -> bool:
        """ Checks if the unit transforming.
        Only works for own units. """
        return self.type_id in transforming and self.is_using_ability(transforming[self.type_id])

    @property_immutable_cache
    def is_repairing(self) -> bool:
        """ Checks if the unit is an SCV or MULE that is currently repairing.
        Only works for own units. """
        return self.is_using_ability(IS_REPAIRING)

    @property
    def add_on_tag(self) -> int:
        """ Returns the tag of the addon of unit. """
        return self._proto.add_on_tag

    @property
    def has_add_on(self) -> bool:
        """ Checks if unit has an addon attached. """
        return bool(self._proto.add_on_tag)

    @property_immutable_cache
    def add_on_land_position(self) -> Point2:
        """ If unit is addon (techlab or reactor), returns the position
        where a terran building has to land to connect to addon """
        return self.position.offset(Point2((-2.5, 0.5)))

    @property_mutable_cache
    def passengers(self) -> Set[Unit]:
        """ Returns the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism. """
        return {Unit(unit, self._bot_object) for unit in self._proto.passengers}

    @property_mutable_cache
    def passengers_tags(self) -> Set[int]:
        """ Returns the tags of the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism. """
        return {unit.tag for unit in self._proto.passengers}

    @property
    def cargo_used(self) -> Union[float, int]:
        """ Returns how much cargo space is currently used in the unit.
        Note that some units take up more than one space. """
        return self._proto.cargo_space_taken

    @property
    def has_cargo(self) -> bool:
        """ Checks if this unit has any units loaded. """
        return bool(self._proto.cargo_space_taken)

    @property
    def cargo_size(self) -> Union[float, int]:
        """ Returns the amount of cargo space the unit needs. """
        return self._type_data.cargo_size

    @property
    def cargo_max(self) -> Union[float, int]:
        """ How much cargo space is available at maximum. """
        return self._proto.cargo_space_max

    @property
    def cargo_left(self) -> Union[float, int]:
        """ Returns how much cargo space is currently left in the unit. """
        return self._proto.cargo_space_max - self._proto.cargo_space_taken

    @property
    def assigned_harvesters(self) -> int:
        """ Returns the number of workers currently gathering resources at a geyser or mining base."""
        return self._proto.assigned_harvesters

    @property
    def ideal_harvesters(self) -> int:
        """ Returns the ideal harverster count for unit.
        3 for gas buildings, 2*n for n mineral patches on that base."""
        return self._proto.ideal_harvesters

    @property
    def surplus_harvesters(self) -> int:
        """ Returns a positive int if unit has too many harvesters mining,
        a negative int if it has too few mining."""
        return self._proto.assigned_harvesters - self._proto.ideal_harvesters

    @property_immutable_cache
    def weapon_cooldown(self) -> Union[int, float]:
        """ Returns the time until the unit can fire again,
        returns -1 for units that can't attack.
        Usage:
        if unit.weapon_cooldown == 0:
            self.do(unit.attack(target))
        elif unit.weapon_cooldown < 0:
            self.do(unit.move(closest_allied_unit_because_cant_attack))
        else:
            self.do(unit.move(retreatPosition)) """
        if self.can_attack:
            return self._proto.weapon_cooldown
        return -1

    @property
    def engaged_target_tag(self) -> int:
        # TODO What does this do?
        return self._proto.engaged_target_tag

    # Unit functions

    def has_buff(self, buff: BuffId) -> bool:
        """ Checks if unit has buff 'buff'. """
        assert isinstance(buff, BuffId), f"{buff} is no BuffId"
        return buff in self.buffs

    def train(self, unit: UnitTypeId, queue: bool = False) -> UnitCommand:
        """ Orders unit to train another 'unit'.
        Usage: self.do(COMMANDCENTER.train(SCV))

        :param unit:
        :param queue: """
        return self(self._bot_object._game_data.units[unit.value].creation_ability.id, queue=queue)

    def build(self, unit: UnitTypeId, position: Union[Point2, Point3] = None, queue: bool = False) -> UnitCommand:
        """ Orders unit to build another 'unit' at 'position'.
        Usage::

            self.do(SCV.build(COMMANDCENTER, position))
            # Target for refinery, assimilator and extractor needs to be the vespene geysir unit, not its position
            self.do(SCV.build(REFINERY, target_vespene_geysir))

        :param unit:
        :param position:
        :param queue:
        """
        # TODO: add asserts to make sure "position" is not a Point2 or Point3 if "unit" is extractor / refinery / assimilator
        return self(self._bot_object._game_data.units[unit.value].creation_ability.id, target=position, queue=queue)

    def build_gas(self, target_geysir: Unit, queue: bool = False) -> UnitCommand:
        """ Orders unit to build another 'unit' at 'position'.
        Usage::

            # Target for refinery, assimilator and extractor needs to be the vespene geysir unit, not its position
            self.do(SCV.build_gas(target_vespene_geysir))

        :param target_geysir:
        :param queue:
        """
        # TODO: add asserts to make sure "target_geysir" is not a Point2 or Point3
        gas_structure_type_id: UnitTypeId = race_gas[self._bot_object.race]
        return self(
            self._bot_object._game_data.units[gas_structure_type_id.value].creation_ability.id,
            target=target_geysir,
            queue=queue,
        )

    def research(self, upgrade: UpgradeId, queue: bool = False) -> UnitCommand:
        """ Orders unit to research 'upgrade'.
        Requires UpgradeId to be passed instead of AbilityId.

        :param upgrade:
        :param queue:
        """
        return self(self._bot_object._game_data.upgrades[upgrade.value].research_ability.id, queue=queue)

    def warp_in(self, unit: UnitTypeId, position: Union[Point2, Point3]) -> UnitCommand:
        """ Orders Warpgate to warp in 'unit' at 'position'. 

        :param unit:
        :param queue:
        """
        normal_creation_ability = self._bot_object._game_data.units[unit.value].creation_ability.id
        return self(warpgate_abilities[normal_creation_ability], target=position)

    def attack(self, target: Union[Unit, Point2, Point3], queue: bool = False) -> UnitCommand:
        """ Orders unit to attack. Target can be a Unit or Point2.
        Attacking a position will make the unit move there and attack everything on its way. 

        :param target:
        :param queue:
        """
        return self(AbilityId.ATTACK, target=target, queue=queue)

    def gather(self, target: Unit, queue: bool = False) -> UnitCommand:
        """ Orders a unit to gather minerals or gas.
        'Target' must be a mineral patch or a gas extraction building. 

        :param target:
        :param queue:
        """
        return self(AbilityId.HARVEST_GATHER, target=target, queue=queue)

    def return_resource(self, target: Unit = None, queue: bool = False) -> UnitCommand:
        """ Orders the unit to return resource. Does not need a 'target'. 

        :param target:
        :param queue:
        """
        return self(AbilityId.HARVEST_RETURN, target=target, queue=queue)

    def move(self, position: Union[Unit, Point2, Point3], queue: bool = False) -> UnitCommand:
        """ Orders the unit to move to 'position'.
        Target can be a Unit (to follow that unit) or Point2. 

        :param position:
        :param queue:
        """
        return self(AbilityId.MOVE_MOVE, target=position, queue=queue)

    def scan_move(self, *args, **kwargs) -> UnitCommand:
        """ Deprecated: This ability redirects to 'AbilityId.ATTACK' """
        return self(AbilityId.SCAN_MOVE, *args, **kwargs)

    def hold_position(self, queue: bool = False) -> UnitCommand:
        """ Orders a unit to stop moving. It will not move until it gets new orders. 

        :param queue:
        """
        return self(AbilityId.HOLDPOSITION, queue=queue)

    def stop(self, queue: bool = False) -> UnitCommand:
        """ Orders a unit to stop, but can start to move on its own
        if it is attacked, enemy unit is in range or other friendly
        units need the space. 

        :param queue:
        """
        return self(AbilityId.STOP, queue=queue)

    def patrol(self, position: Union[Point2, Point3], queue: bool = False) -> UnitCommand:
        """ Orders a unit to patrol between position it has when the command starts and the target position.
        Can be queued up to seven patrol points. If the last point is the same as the starting
        point, the unit will patrol in a circle. 

        :param position:
        :param queue:
        """
        return self(AbilityId.PATROL, target=position, queue=queue)

    def repair(self, repair_target: Unit, queue: bool = False) -> UnitCommand:
        """ Order an SCV or MULE to repair. 

        :param repair_target:
        :param queue:
        """
        return self(AbilityId.EFFECT_REPAIR, target=repair_target, queue=queue)

    def __hash__(self):
        return self.tag

    def __eq__(self, other):
        try:
            return self.tag == other.tag
        except:
            return False

    def __call__(self, ability, target=None, queue: bool = False):
        return UnitCommand(ability, self, target=target, queue=queue)
