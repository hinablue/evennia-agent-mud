"""Helpers for authenticating MCP bearer tokens inside Evennia."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from evennia.accounts.models import AccountDB


class MCPTokenError(ValueError):
    """Raised when an MCP token cannot authenticate."""


@dataclass
class MCPTokenIdentity:
    """Resolved Evennia identity for one MCP token."""

    account: Any
    character: Optional[Any]
    scopes: list[str]
    token_id: str = ""


DEFAULT_REGISTRY_NAME = "mcp_tokens.json"


def get_registry_path() -> Path:
    """Return the MCP token registry path.

    The path can be configured with ``MCP_TOKEN_REGISTRY``. If omitted, the game
    looks for ``server/conf/mcp_tokens.json`` under ``settings.GAME_DIR``.
    """

    configured = os.environ.get("MCP_TOKEN_REGISTRY") or getattr(
        settings, "MCP_TOKEN_REGISTRY", ""
    )
    if configured:
        return Path(configured).expanduser()
    return Path(settings.GAME_DIR) / "server" / "conf" / DEFAULT_REGISTRY_NAME


def get_token_secret() -> str:
    """Return the secret used to hash opaque MCP tokens."""

    secret = os.environ.get("MCP_TOKEN_SECRET") or getattr(settings, "MCP_TOKEN_SECRET", "")
    if not secret:
        secret = settings.SECRET_KEY
    return str(secret)


def hash_mcp_token(token: str, secret: Optional[str] = None) -> str:
    """Hash an opaque MCP token with the server secret.

    Args:
        token: Raw bearer token received from the MCP client.
        secret: Optional override for tests or external provisioning.

    Returns:
        A stable SHA-256 hex digest suitable for storing in the registry.
    """

    token = (token or "").strip()
    if not token:
        raise MCPTokenError("MCP token 不可為空。")
    secret = get_token_secret() if secret is None else secret
    payload = f"{secret}:{token}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_token_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the server-side MCP token registry JSON."""

    registry_path = path or get_registry_path()
    if not registry_path.exists():
        raise MCPTokenError(f"找不到 MCP token registry：{registry_path}")
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MCPTokenError(f"MCP token registry JSON 格式錯誤：{exc}") from exc
    if not isinstance(data, dict):
        raise MCPTokenError("MCP token registry 必須是 JSON object。")
    return data


def _iter_entries(registry: Dict[str, Any]) -> Iterable[tuple[str, Dict[str, Any]]]:
    tokens = registry.get("tokens", registry)
    if not isinstance(tokens, dict):
        raise MCPTokenError("MCP token registry 的 tokens 必須是 object。")
    for token_id, entry in tokens.items():
        if not isinstance(entry, dict):
            continue
        yield str(token_id), entry


def _find_account(account_ref: Any):
    """Resolve an account by id or case-insensitive username."""

    if account_ref in (None, ""):
        raise MCPTokenError("token registry 缺少 account。")
    if isinstance(account_ref, int) or str(account_ref).isdigit():
        account = AccountDB.objects.filter(id=int(account_ref)).first()
    else:
        account = AccountDB.objects.filter(username__iexact=str(account_ref)).first()
    if not account:
        raise MCPTokenError(f"找不到 token 綁定帳號：{account_ref}")
    return account


def _find_character(account, character_ref: Any):
    """Resolve a character in the account roster."""

    if character_ref in (None, ""):
        primary = getattr(account.db, "primary_character", None)
        if primary:
            return primary
        last_puppet = getattr(account.db, "_last_puppet", None)
        if last_puppet:
            return last_puppet
        characters = list(account.characters.all())
        return characters[0] if characters else None

    requested = str(character_ref).lower()
    for character in account.characters.all():
        if str(character.id) == requested or character.key.lower() == requested:
            return character
    raise MCPTokenError(f"角色 `{character_ref}` 不屬於帳號 `{account.key}`。")


def authenticate_mcp_token(token: str, character: Optional[str] = None) -> MCPTokenIdentity:
    """Authenticate a raw MCP bearer token and resolve an Evennia identity.

    Registry format::

        {
          "tokens": {
            "hina-admin": {
              "token_hash": "sha256(secret:token)",
              "account": "hina",
              "character": "Hina",
              "scopes": ["player", "admin"],
              "enabled": true
            }
          }
        }

    ``character`` may narrow the token to another character owned by the same
    account only when the entry sets ``allow_character_override`` to true.
    """

    token_hash = hash_mcp_token(token)
    registry = load_token_registry()
    for token_id, entry in _iter_entries(registry):
        stored_hash = str(entry.get("token_hash") or entry.get("hash") or "")
        if not stored_hash or not hmac.compare_digest(stored_hash, token_hash):
            continue
        if entry.get("enabled", True) is False:
            raise MCPTokenError("這個 MCP token 已停用。")
        account = _find_account(entry.get("account"))
        character_ref = entry.get("character")
        if character and entry.get("allow_character_override", False):
            character_ref = character
        elif character and character != character_ref:
            raise MCPTokenError("這個 MCP token 不允許覆寫 character。")
        resolved_character = _find_character(account, character_ref)
        scopes = [str(scope) for scope in entry.get("scopes", ["player"])]
        return MCPTokenIdentity(
            account=account,
            character=resolved_character,
            scopes=scopes,
            token_id=token_id,
        )
    raise MCPTokenError("MCP token 無效。")
