"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from evennia import default_cmds

from evennia.contrib.grid import extended_room, mapbuilder, simpledoor, slow_exit
from evennia.contrib.grid.ingame_map_display import MapDisplayCmdSet
from evennia.contrib.grid.xyzgrid.commands import XYZGridCmdSet
from typeclasses.llm_npc import CmdLocalLLMTalk

from evennia.contrib.base_systems.building_menu import GenericBuildingCmd
from evennia.contrib.base_systems.ingame_reports import ReportsCmdSet
from evennia.contrib.game_systems.achievements.achievements import CmdAchieve
from evennia.contrib.game_systems.barter import CmdsetTrade
from evennia.contrib.game_systems.clothing import ClothedCharacterCmdSet
from evennia.contrib.game_systems.containers import ContainerCmdSet
from evennia.contrib.game_systems.gendersub import SetGender
from evennia.contrib.game_systems.storage import StorageCmdSet
from evennia.contrib.rpg.rpsystem import RPSystemCmdSet

from .account_character_commands import (
    CmdCharacterRoster,
    CmdLockedCharCreate,
    CmdLockedIC,
)
from .combat_admin import CmdAgentCombat
from .combat_commands import (
    CmdCombatAttack,
    CmdCombatSkill,
    CmdCombatFlee,
    CmdPick,
    CmdCast,
)
from .combat_socket import CmdSocketGem
from .equipment_admin import CmdAgentWeapon
from .npc_admin import CmdAgentNPC
from .object_admin import CmdAgentObject
from .player_admin import CmdAgentPlayer
from .player_commands import CmdStatus, CmdInventory, CmdEquipment, CmdShop, CmdBuy
from .account_admin import CmdAgentAccount
from .quest_admin import CmdAgentQuest
from .room_admin import CmdAgentRoom
from .world_admin import CmdAgentWorld
from .magic_admin import CmdAgentMagic


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(extended_room.ExtendedRoomCmdSet)
        self.add(MapDisplayCmdSet)
        self.add(XYZGridCmdSet())
        self.add(mapbuilder.CmdMapBuilder())
        self.add(simpledoor.SimpleDoorCmdSet)
        self.add(slow_exit.SlowExitCmdSet)
        self.add(CmdLocalLLMTalk())
        self.add(GenericBuildingCmd())
        self.add(CmdAchieve)
        self.add(CmdsetTrade)
        self.add(ClothedCharacterCmdSet)
        self.add(ContainerCmdSet)
        self.add(SetGender())
        self.add(StorageCmdSet)
        self.add(RPSystemCmdSet())

        self.add(CmdCombatAttack())
        self.add(CmdCombatSkill())
        self.add(CmdCombatFlee())
        self.add(CmdPick())
        self.add(CmdSocketGem())
        self.add(CmdCast())

        self.add(CmdAgentWorld())
        self.add(CmdAgentNPC())
        self.add(CmdAgentPlayer())
        self.add(CmdAgentAccount())
        self.add(CmdAgentObject())
        self.add(CmdAgentCombat())
        self.add(CmdAgentQuest())
        self.add(CmdAgentRoom())
        self.add(CmdAgentWeapon())
        self.add(CmdAgentMagic())

        self.add(CmdStatus())
        self.add(CmdInventory())
        self.add(CmdEquipment())
        self.add(CmdShop())
        self.add(CmdBuy())


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(ReportsCmdSet)
        self.add(CmdLockedIC())
        self.add(CmdLockedCharCreate())
        self.add(CmdCharacterRoster())


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #