#!/usr/bin/env python3
"""將 markdown、Python 註解/文件字串和 gettext 目錄批次本地化到 zh-Hant。"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound

ENG_RE = re.compile(r"[A-Za-z]{3,}")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
URL_RE = re.compile(r"https?://\S+")
MASK_RE = re.compile(r"(`[^`]+`|\{[^{}]+\}|\|[a-zA-Z]|\$[A-Za-z_]+\([^)]*\)|<[^>]+>)")
COMMENT_SKIP_RE = re.compile(r"^(?:!/|coding[:=]|noqa|type:|fmt:|pragma:|pylint:)")
SKIP_DIRS = {".git", ".agents", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "node_modules"}
SKIP_PARTS = {"tests", "migrations"}
SKIP_FILES = {"AGENTS.md", "LICENSE.md", "license.md"}


@dataclass
class Stats:
    markdown_files: int = 0
    markdown_lines: int = 0
    python_files: int = 0
    python_docstrings: int = 0
    python_comments: int = 0
    po_files: int = 0
    po_entries: int = 0


class TranslatorCache:
    def __init__(self) -> None:
        self.translator = GoogleTranslator(source="en", target="zh-TW")
        self.cache: dict[str, str] = {}

    def translate_many(self, texts: list[str]) -> list[str]:
        missing = [text for text in dict.fromkeys(texts) if text not in self.cache]
        batch_size = 50
        for idx in range(0, len(missing), batch_size):
            batch = missing[idx : idx + batch_size]
            try:
                translated_batch = self.translator.translate_batch(batch)
            except Exception:
                translated_batch = []
                for text in batch:
                    try:
                        translated_batch.append(self.translator.translate(text))
                    except (TranslationNotFound, Exception):
                        translated_batch.append(text)
            for source, target in zip(batch, translated_batch):
                self.cache[source] = target or source
        return [self.cache.get(text, text) for text in texts]


def looks_english(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if URL_RE.fullmatch(stripped):
        return False
    return bool(ENG_RE.search(stripped)) and not bool(CJK_RE.search(stripped))


def mask_tokens(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        key = f"__MASK_{len(mapping)}__"
        mapping[key] = match.group(0)
        return key

    masked = MASK_RE.sub(repl, text)
    masked = URL_RE.sub(repl, masked)
    return masked, mapping


def unmask_tokens(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


def translate_text(cache: TranslatorCache, text: str) -> str:
    if not looks_english(text):
        return text
    masked, mapping = mask_tokens(text)
    translated = cache.translate_many([masked])[0]
    translated = unmask_tokens(translated, mapping)
    return translated


def iter_files(root: Path, suffix: str) -> Iterable[Path]:
    for path in root.rglob(f"*{suffix}"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def translate_markdown_file(path: Path, cache: TranslatorCache) -> int:
    if path.name in SKIP_FILES:
        return 0
    text = path.read_text(encoding="utf-8")
    changed = 0
    in_code_block = False
    out_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block
            out_lines.append(line)
            continue
        if in_code_block or not looks_english(stripped):
            out_lines.append(line)
            continue
        prefix_match = re.match(r"^(\s*(?:[#>*-]|\d+\.)?\s*)", line)
        prefix = prefix_match.group(1) if prefix_match else ""
        body = line[len(prefix) :].rstrip("\n")
        translated = translate_text(cache, body)
        if translated != body:
            changed += 1
        out_lines.append(prefix + translated + ("\n" if line.endswith("\n") else ""))
    if changed:
        path.write_text("".join(out_lines), encoding="utf-8")
    return changed


def get_docstring_positions(tree: ast.AST) -> set[tuple[int, int]]:
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                positions.add((first.value.lineno, first.value.col_offset))
    return positions


STRING_PREFIX_RE = re.compile(r"^([rubfRUBF]*)(['\"]{3}|['\"])", re.DOTALL)


def rebuild_string_literal(token_string: str, new_text: str) -> str:
    match = STRING_PREFIX_RE.match(token_string)
    if not match:
        return repr(new_text)
    prefix, quote = match.groups()
    safe_prefix = "".join(ch for ch in prefix if ch.lower() in {"r", "u"})
    if quote in {"'''", '"""'}:
        body = new_text.replace("\\", "\\\\")
        if quote == '"""':
            body = body.replace('"""', '\\"\\"\\"')
        else:
            body = body.replace("'''", "\\'\\'\\'")
        return f"{safe_prefix}{quote}{body}{quote}"
    body = json.dumps(new_text, ensure_ascii=False)
    if quote == "'":
        body = body.replace('"', "'")
    return f"{safe_prefix}{body}"


def translate_python_file(path: Path, cache: TranslatorCache) -> tuple[int, int]:
    if any(part in SKIP_PARTS for part in path.parts):
        return 0, 0
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    doc_positions = get_docstring_positions(tree)
    out_tokens = []
    doc_count = 0
    comment_count = 0
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.STRING and tok.start in doc_positions:
            try:
                value = ast.literal_eval(tok.string)
            except Exception:
                out_tokens.append(tok)
                continue
            translated = translate_text(cache, value)
            if translated != value:
                tok = tokenize.TokenInfo(tok.type, rebuild_string_literal(tok.string, translated), tok.start, tok.end, tok.line)
                doc_count += 1
        elif tok.type == tokenize.COMMENT:
            body = tok.string.lstrip("#").strip()
            if body and not COMMENT_SKIP_RE.match(body) and looks_english(body):
                translated = translate_text(cache, body)
                if translated != body:
                    indent = tok.string.split("#", 1)[0]
                    tok = tokenize.TokenInfo(tok.type, f"{indent}# {translated}", tok.start, tok.end, tok.line)
                    comment_count += 1
        out_tokens.append(tok)
    if doc_count or comment_count:
        path.write_text(tokenize.untokenize(out_tokens), encoding="utf-8")
    return doc_count, comment_count


def compile_po(path: Path) -> None:
    subprocess.run([
        sys.executable,
        "-c",
        (
            "import polib; "
            f"po=polib.pofile({path.as_posix()!r}); "
            f"po.save_as_mofile({path.with_suffix('.mo').as_posix()!r})"
        ),
    ], check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--translate-markdown", action="store_true")
    parser.add_argument("--translate-python", action="store_true")
    parser.add_argument("--compile-po", action="store_true")
    parser.add_argument("--skip-file", action="append", default=[])
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    skip_files = {str((root / item).resolve()) if not item.startswith("/") else str(Path(item).resolve()) for item in args.skip_file}
    cache = TranslatorCache()
    stats = Stats()

    if args.translate_markdown:
        for path in iter_files(root, ".md"):
            if str(path.resolve()) in skip_files:
                continue
            changed = translate_markdown_file(path, cache)
            if changed:
                stats.markdown_files += 1
                stats.markdown_lines += changed

    if args.translate_python:
        for path in iter_files(root, ".py"):
            if str(path.resolve()) in skip_files:
                continue
            docs, comments = translate_python_file(path, cache)
            if docs or comments:
                stats.python_files += 1
                stats.python_docstrings += docs
                stats.python_comments += comments

    if args.compile_po:
        for path in iter_files(root, ".po"):
            if str(path.resolve()) in skip_files:
                continue
            compile_po(path)
            stats.po_files += 1
            stats.po_entries += 1

    print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
