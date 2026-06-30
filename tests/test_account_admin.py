"""Tests for account admin helpers and command routing."""

from __future__ import annotations

import importlib
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch


def _install_evennia_stubs():
    """Install minimal Evennia stubs needed by account admin tests."""

    evennia = ModuleType("evennia")
    evennia.search_account = MagicMock(return_value=[])
    sys.modules["evennia"] = evennia

    accounts_models = ModuleType("evennia.accounts.models")
    accounts_models.AccountDB = SimpleNamespace(objects=SimpleNamespace(all=lambda: []))

    class Permission:
        """Minimal permission stub."""

        class DoesNotExist(Exception):
            """Raised when a permission is missing."""

        objects = SimpleNamespace(get=MagicMock())

    accounts_models.Permission = Permission
    sys.modules["evennia.accounts.models"] = accounts_models

    accounts_accounts = ModuleType("evennia.accounts.accounts")

    class DefaultAccount:
        """Minimal DefaultAccount stub."""

        create = MagicMock(return_value=(None, []))

    accounts_accounts.DefaultAccount = DefaultAccount
    sys.modules["evennia.accounts.accounts"] = accounts_accounts

    utils_utils = ModuleType("evennia.utils.utils")
    utils_utils.make_iter = lambda value: (
        value if isinstance(value, (list, tuple, set)) else [value]
    )
    sys.modules["evennia.utils.utils"] = utils_utils

    utils_search = ModuleType("evennia.utils.search")
    utils_search.search_object = MagicMock(return_value=[])
    sys.modules["evennia.utils.search"] = utils_search

    utils_module = ModuleType("evennia.utils")
    utils_module.logger = SimpleNamespace(log_info=MagicMock(), log_err=MagicMock())
    sys.modules["evennia.utils"] = utils_module

    commands_command = ModuleType("commands.command")

    class MuxCommand:
        """Minimal MuxCommand base stub."""

    commands_command.MuxCommand = MuxCommand
    sys.modules["commands.command"] = commands_command

    kingdom_module = ModuleType("world.kingdom")
    kingdom_module.get_kingdom_by_name = MagicMock(return_value=None)
    kingdom_module.get_kingdom_by_king = MagicMock(return_value=None)
    sys.modules["world.kingdom"] = kingdom_module


_install_evennia_stubs()

account_tools = importlib.import_module("world.account_tools")
account_admin = importlib.import_module("commands.account_admin")

AccountSpecError = account_tools.AccountSpecError
CmdAgentAccount = account_admin.CmdAgentAccount
set_account_role = account_tools.set_account_role
ensure_first_player_account_is_gm = account_tools.ensure_first_player_account_is_gm


def _fake_char_count(count):
    """Build a fake character relation object with a stable count."""

    return SimpleNamespace(all=lambda: [object()] * count, count=lambda: count)


class FakeCaller:
    """Collect command output for assertions."""

    def __init__(self, permissions=None, is_king=False):
        self.messages = []
        self.account = SimpleNamespace(
            permissions=SimpleNamespace(all=lambda: list(permissions or []))
        )
        self.db = SimpleNamespace(is_king=is_king)

    def msg(self, text):
        self.messages.append(text)


class AccountToolsTests(unittest.TestCase):
    """Unit tests for world.account_tools."""

    def test_create_account_creates_live_account(self):
        """Creating an account should delegate to Evennia's account factory."""

        account = SimpleNamespace(key="hinablue", permissions=SimpleNamespace(all=lambda: []))

        default_account = sys.modules["evennia.accounts.accounts"].DefaultAccount
        with patch.object(
            default_account,
            "create",
            return_value=(account, []),
        ) as creator:
            result = account_tools.create_account(
                "hinablue",
                "stardust11",
                email="hina@example.com",
            )

        creator.assert_called_once_with(
            username="hinablue",
            password="stardust11",
            email="hina@example.com",
        )
        self.assertIn("已建立 Account `hinablue`", result["message"])
        self.assertIn("hina@example.com", result["message"])

    def test_create_account_surfaces_evennia_validation_errors(self):
        """Evennia validation failures should become AccountSpecError messages."""

        default_account = sys.modules["evennia.accounts.accounts"].DefaultAccount
        with patch.object(
            default_account,
            "create",
            return_value=(None, ["A user with that username already exists."]),
        ):
            with self.assertRaises(AccountSpecError) as err:
                account_tools.create_account("hinablue", "stardust11")

        self.assertIn("建立帳號失敗", str(err.exception))
        self.assertIn("A user with that username already exists.", str(err.exception))

    def test_set_account_role_normalizes_hierarchy_permissions(self):
        """Setting a hierarchy role should replace older hierarchy permissions."""

        existing_perms = ["Admin", "Player"]
        account = SimpleNamespace(
            key="hinablue",
            permissions=SimpleNamespace(
                all=lambda: existing_perms,
                add=MagicMock(),
                remove=MagicMock(),
            ),
            save=MagicMock(),
        )

        with patch.object(account_tools, "_get_account_or_error", return_value=account):
            result = set_account_role("hinablue", "King")

        self.assertEqual(result["role"], "King")
        self.assertIn("`King`", result["message"])
        account.permissions.remove.assert_any_call("Admin")
        account.permissions.remove.assert_any_call("Player")
        account.permissions.add.assert_called_once_with("King")
        account.save.assert_called_once_with()

    def test_ensure_first_player_account_is_gm_promotes_first_bound_account(self):
        """First bound account should become GM when no staff account exists."""

        first_character = SimpleNamespace(
            key="Hina",
            permissions=SimpleNamespace(
                all=lambda: ["Player"],
                add=MagicMock(),
                remove=MagicMock(),
            ),
            save=MagicMock(),
        )
        first_account = SimpleNamespace(
            key="hinablue",
            permissions=SimpleNamespace(
                all=lambda: ["Player"],
                add=MagicMock(),
                remove=MagicMock(),
            ),
            characters=SimpleNamespace(all=lambda: [first_character]),
            save=MagicMock(),
        )
        second_account = SimpleNamespace(
            key="other",
            permissions=SimpleNamespace(all=lambda: []),
            characters=SimpleNamespace(all=lambda: []),
        )

        with patch.object(account_tools.AccountDB.objects, "all", return_value=[first_account, second_account]):
            result = ensure_first_player_account_is_gm()

        self.assertTrue(result["promoted"])
        self.assertIs(result["account"], first_account)
        self.assertIs(result["character"], first_character)
        first_account.permissions.add.assert_any_call("Admin")
        first_account.permissions.add.assert_any_call("GM")
        first_character.permissions.add.assert_any_call("Admin")
        first_character.permissions.add.assert_any_call("GM")

    def test_ensure_first_player_account_is_gm_skips_when_staff_exists(self):
        """Bootstrap promotion should not overwrite an existing staff account."""

        staff_account = SimpleNamespace(
            key="staff",
            permissions=SimpleNamespace(all=lambda: ["Admin"]),
            characters=SimpleNamespace(all=lambda: []),
        )
        player_account = SimpleNamespace(
            key="hinablue",
            permissions=SimpleNamespace(
                all=lambda: ["Player"],
                add=MagicMock(),
                remove=MagicMock(),
            ),
            characters=SimpleNamespace(all=lambda: [SimpleNamespace(key="Hina")]),
            save=MagicMock(),
        )

        with patch.object(account_tools.AccountDB.objects, "all", return_value=[staff_account, player_account]):
            result = ensure_first_player_account_is_gm()

        self.assertFalse(result["promoted"])
        player_account.permissions.add.assert_not_called()

    def test_delete_account_deletes_live_account(self):
        """Deleting a normal account should call Evennia's delete hook."""

        account = SimpleNamespace(
            key="hinablue",
            is_superuser=False,
            characters=_fake_char_count(2),
            delete=MagicMock(return_value=True),
        )

        with patch.object(account_tools, "_get_account_or_error", return_value=account):
            result = account_tools.delete_account("hinablue")

        account.delete.assert_called_once_with()
        self.assertIn("已刪除 Account `hinablue`", result["message"])
        self.assertIn("2 個角色", result["message"])

    def test_delete_account_rejects_superuser(self):
        """Superuser accounts should be protected from accidental deletion."""

        account = SimpleNamespace(
            key="superuser",
            is_superuser=True,
            characters=_fake_char_count(0),
            delete=MagicMock(return_value=True),
        )

        with patch.object(account_tools, "_get_account_or_error", return_value=account):
            with self.assertRaises(AccountSpecError) as err:
                account_tools.delete_account("superuser")

        self.assertIn("不能刪除 superuser", str(err.exception))
        account.delete.assert_not_called()


class CmdAgentAccountTests(unittest.TestCase):
    """Command routing tests for @agentaccount."""

    def _make_cmd(self, permissions=None, is_king=False):
        cmd = object.__new__(CmdAgentAccount)
        cmd.caller = FakeCaller(permissions=permissions, is_king=is_king)
        cmd.switches = []
        cmd.args = ""
        cmd.lhs = ""
        cmd.rhs = None
        cmd.lhslist = []
        cmd.rhslist = []
        cmd.arglist = []
        return cmd

    def test_handle_delete_requires_account_name(self):
        """The delete switch should require an explicit account name."""

        cmd = self._make_cmd(permissions=["Admin"])

        with self.assertRaises(AccountSpecError) as err:
            cmd._handle_delete()

        self.assertIn("delete 格式需要 `帳號`", str(err.exception))

    def test_handle_create_requires_account_and_password(self):
        """The create switch should require account and password input."""

        cmd = self._make_cmd()

        with self.assertRaises(AccountSpecError) as err:
            cmd._handle_create()

        self.assertIn("create 格式需要 `帳號=密碼`", str(err.exception))

    def test_func_routes_create_switch(self):
        """The public command entrypoint should dispatch /create correctly."""

        cmd = self._make_cmd()
        cmd.switches = ["create"]
        cmd.lhs = "hinablue"
        cmd.rhs = "stardust11|hina@example.com"

        with patch(
            "commands.account_admin.create_account",
            return_value={"message": "建立完成"},
        ) as creator:
            cmd.func()

        creator.assert_called_once_with(
            "hinablue",
            "stardust11",
            email="hina@example.com",
        )
        self.assertEqual(cmd.caller.messages[-1], "建立完成")

    def test_func_rejects_gm_permission_in_addperm(self):
        """@agentaccount should refuse GM-tier permission changes."""

        cmd = self._make_cmd()
        cmd.switches = ["addperm"]
        cmd.lhs = "hinablue"
        cmd.rhs = "GM"
        fake_account = SimpleNamespace(key="hinablue")

        with patch("commands.account_admin._find_exact_account", return_value=fake_account):
            cmd.func()

        self.assertIn("@agentaccount 只能管理 King/Player 權限", cmd.caller.messages[-1])

    def test_func_routes_delete_switch(self):
        """The public command entrypoint should dispatch /delete correctly."""

        cmd = self._make_cmd(permissions=["Admin"])
        cmd.switches = ["delete"]
        cmd.args = "hinablue"
        fake_account = SimpleNamespace(key="hinablue")

        with patch(
            "commands.account_admin.delete_account",
            return_value={"message": "刪除完成"},
        ) as deleter, patch(
            "commands.account_admin._find_exact_account",
            return_value=fake_account,
        ):
            cmd.func()

        deleter.assert_called_once_with("hinablue")
        self.assertEqual(cmd.caller.messages[-1], "刪除完成")

    def test_handle_delete_rejects_plain_king(self):
        """Kings without GM/Developer/Admin should not be able to delete accounts."""

        cmd = self._make_cmd(permissions=["King"], is_king=True)
        cmd.args = "hinablue"

        with self.assertRaises(AccountSpecError) as err:
            cmd._handle_delete()

        self.assertIn("delete 僅限 GM/Developer/Admin 使用", str(err.exception))


if __name__ == "__main__":
    unittest.main()
