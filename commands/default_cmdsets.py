"""命令集

遊戲中的所有命令必須分組在一個命令集中。  給定的命令
可以是任意數量的 cmdset 的一部分，並且可以添加/刪除 cmdset
並在運行時合併到實體上。

若要建立新指令來填入 cmdset，請參閱
`commands/command.py`。

該模組包裝了 Evennia 的預設命令集；使他們覆寫
從預設隊列中新增/刪除命令。您可以創建您的
透過繼承或直接從 `evennia.CmdSet` 來擁有自己的 cmdset。"""

from evennia import default_cmds
from evennia.contrib.base_systems.building_menu import GenericBuildingCmd
from evennia.contrib.base_systems.ingame_reports import ReportsCmdSet
from evennia.contrib.game_systems.achievements.achievements import CmdAchieve
from evennia.contrib.game_systems.barter import CmdsetTrade
from evennia.contrib.game_systems.containers import ContainerCmdSet
from evennia.contrib.game_systems.gendersub import SetGender
from evennia.contrib.game_systems.storage import StorageCmdSet
from evennia.contrib.grid import extended_room, mapbuilder, simpledoor, slow_exit
from evennia.contrib.grid.ingame_map_display import MapDisplayCmdSet
from evennia.contrib.grid.xyzgrid.commands import XYZGridCmdSet
from evennia.contrib.rpg.rpsystem import RPSystemCmdSet

from typeclasses.llm_npc import CmdLocalLLMTalk

from .account_admin import CmdAgentAccount
from .account_character_commands import (
    CmdCharacterRoster,
    CmdChineseOOC,
    CmdChineseOOCLook,
    CmdLockedCharCreate,
    CmdLockedIC,
)
from .combat_admin import CmdAgentCombat
from .combat_commands import (
    CmdCast,
    CmdCombatAttack,
    CmdCombatFlee,
    CmdCombatSkill,
    CmdPick,
)
from .combat_socket import CmdSocketGem
from .equipment_admin import CmdAgentWeapon
from .kingdom_admin import CmdKingdomAdmin
from .magic_admin import CmdAgentMagic
from .npc_admin import CmdAgentNPC
from .object_admin import CmdAgentObject
from .player_admin import CmdAgentPlayer
from .player_commands import (
    CmdBuy,
    CmdCoverEquipment,
    CmdEquipment,
    CmdInventory,
    CmdRemoveEquipment,
    CmdShop,
    CmdStatus,
    CmdUncoverEquipment,
    CmdWearEquipment,
)
from .quest_admin import CmdAgentQuest
from .room_admin import CmdAgentRoom
from .world_admin import CmdAgentWorld


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """`CharacterCmdSet` 包含通用遊戲內指令，例如 `look`、
    `get` 等可用於遊戲中的角色物件。它合併於
    當帳號操縱角色時的 `AccountCmdSet` 。"""

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """填充 cmdset"""
        super().at_cmdset_creation()

        #
        # 您在下面新增的任何命令都會覆寫預設命令。
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
        self.add(CmdKingdomAdmin())
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
        self.add(CmdWearEquipment())
        self.add(CmdRemoveEquipment())
        self.add(CmdCoverEquipment())
        self.add(CmdUncoverEquipment())
        self.add(CmdShop())
        self.add(CmdBuy())

        # Remove commands
        for cmdname in (
            "@open",
            "force",
            "@mapbuilder",
            "@userpassword",
            "userpassword",
            "batchcode",
            "batchcommands",
            "examine",
            "mapbuilder",
            "@roomstate",
            "sethelp",
            "unlink",
            "roomstate",
            "ban",
            "boot",
            "emit",
            "perm",
            "unban",
            "wall",
            "shutdown",
            "reset",
            "py",
            "evennia",
            "@alias",
            "@cmdsets",
            "@copy",
            "@cpattr",
            "@detail",
            "@dig",
            "@edit",
            "@examine",
            "@find",
            "@link",
            "@lock",
            "@mvattr",
            "@name",
            "@set",
            "@sethelp",
            "@sethome",
            "@spawn",
            "@tag",
            "@teleport",
            "@tunnel",
            "@typeclass",
            "@unlink",
            "@wipe",
            "@py",
            "@time",
            "@about",
            "@objects",
            "@reset",
            "@scripts",
            "@server",
            "@service",
            "@shutdown",
            "@tasks",
            "@tickers",
            "characters",
            "charcreate",
            "chardelete",
        ):
            self.remove(cmdname)


class AccountCmdSet(default_cmds.AccountCmdSet):
    """這是帳戶始終可用的 cmdset。它是
    當帳戶操縱 a 時與 `CharacterCmdSet` 結合
    性格。它包含遊戲帳號特定的指令、頻道
    命令等"""

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """填充 cmdset"""
        super().at_cmdset_creation()
        #
        # 您在下面新增的任何命令都會覆寫預設命令。
        #
        self.add(ReportsCmdSet)
        self.add(CmdChineseOOCLook())
        self.add(CmdChineseOOC())
        self.add(CmdLockedIC())
        self.add(CmdLockedCharCreate())
        self.add(CmdCharacterRoster())

        # Remove commands
        for cmdname in (
            "@open",
            "force",
            "@mapbuilder",
            "@userpassword",
            "userpassword",
            "batchcode",
            "batchcommands",
            "examine",
            "mapbuilder",
            "@roomstate",
            "sethelp",
            "unlink",
            "roomstate",
            "ban",
            "boot",
            "emit",
            "perm",
            "unban",
            "wall",
            "shutdown",
            "reset",
            "py",
            "evennia",
            "@alias",
            "@cmdsets",
            "@copy",
            "@cpattr",
            "@detail",
            "@dig",
            "@edit",
            "@examine",
            "@find",
            "@link",
            "@lock",
            "@mvattr",
            "@name",
            "@set",
            "@sethelp",
            "@sethome",
            "@spawn",
            "@tag",
            "@teleport",
            "@tunnel",
            "@typeclass",
            "@unlink",
            "@wipe",
            "@py",
            "@time",
            "@about",
            "@objects",
            "@reset",
            "@scripts",
            "@server",
            "@service",
            "@shutdown",
            "@tasks",
            "@tickers",
            "characters",
            "charcreate",
            "chardelete",
        ):
            self.remove(cmdname)


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """登入前會話可用的命令集。這
    包含建立新帳戶、登入等命令。"""

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """填充 cmdset"""
        super().at_cmdset_creation()
        #
        # 您在下面新增的任何命令都會覆寫預設命令。
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """登入後，此 cmdset 在會話層級可用。
    預設為空。"""

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """這是在 cmdset 中定義的唯一方法，在
        它的創造。它應該用命令實例填充該集合。

        例如，我們只需新增空的基本 `Command` 物件。
        它會列印一些資訊。"""
        super().at_cmdset_creation()
        #
        # 您在下面新增的任何命令都會覆寫預設命令。
        #
