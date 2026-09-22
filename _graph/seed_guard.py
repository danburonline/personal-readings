"""A shared advisory single-writer guard for the canonical JSONL seed.

Cooperating helpers fail fast on contention. Manual editors do not honour this
lock; digest checks catch intervening edits, not an arbitrary simultaneous write.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def fingerprint(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def require_unchanged(path: Path, expected: str | None) -> None:
    if fingerprint(path) != expected:
        raise RuntimeError(f"Seed changed during maintenance; refusing to write or activate: {path}")


class SeedGuard:
    def __init__(self, seed: Path):
        self.seed = seed.resolve()
        self.lock = self.seed.with_name(self.seed.name + ".write-lock")
        self.expected: str | None = None

    def __enter__(self):
        try:
            self.lock.mkdir()
        except FileExistsError as exc:
            raise RuntimeError(
                f"Seed maintenance is already locked: {self.lock}. "
                "Do not remove it unless its owning process has stopped."
            ) from exc
        try:
            self.expected = fingerprint(self.seed)
        except BaseException:
            self.lock.rmdir()
            raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.lock.rmdir()

    def check(self):
        require_unchanged(self.seed, self.expected)

    def append(self, lines: list[str]):
        self.check()
        with self.seed.open("a", encoding="utf-8") as handle:
            handle.writelines(line + "\n" for line in lines)
            handle.flush()
        self.expected = fingerprint(self.seed)
