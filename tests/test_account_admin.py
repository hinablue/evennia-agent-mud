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

    utils_utils = ModuleType("evennia.utils.utils")
    utils_utils.make_iter = lambda value: (
        value if isinstance(value, (list, tuple, set)) else [value]
    )
    sys.modules["evennia.utils.utils"] = utils_utils

    commands_command = ModuleType("commands.command")

    class MuxCommand:
        """Minimal MuxCommand base stub."""

    commands_command.MuxCommand = MuxCommand
    sys.modules["commands.command"] = commands_command


_install_evennia_stubs()

account_tools = importlib.import_module("world.account_tools")
account_admin = importlib.import_module("commands.account_admin")

AccountSpecError = account_tools.AccountSpecError
CmdAgentAccount = account_admin.CmdAgentAccount


def _fake_char_count(count):
    """Build a fake character relation object with a stable count."""

    return SimpleNamespace(all=lambda: [object()] * count, count=lambda: count)


class FakeCaller:
    """Collect command output for assertions."""

    def __init__(self):
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


class AccountToolsTests(unittest.TestCase):
    """Unit tests for world.account_tools."""

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

    def _make_cmd(self):
        cmd = object.__new__(CmdAgentAccount)
        cmd.caller = FakeCaller()
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

        cmd = self._make_cmd()

        with self.assertRaises(AccountSpecError) as err:
            cmd._handle_delete()

        self.assertIn("delete 格式需要 `帳號`", str(err.exception))

    def test_func_routes_delete_switch(self):
        """The public command entrypoint should dispatch /delete correctly."""

        cmd = self._make_cmd()
        cmd.switches = ["delete"]
        cmd.args = "hinablue"

        with patch(
            "commands.account_admin.delete_account",
            return_value={"message": "刪除完成"},
        ) as deleter:
            cmd.func()

        deleter.assert_called_once_with("hinablue")
        self.assertEqual(cmd.caller.messages[-1], "刪除完成")


if __name__ == "__main__":
    unittest.main()
