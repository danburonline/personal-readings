#!/usr/bin/env python3
"""Build and validate a separate Nanograph database; activate only on request.

Run from any directory. No PDF, seed or existing database is overwritten.
Stop other database users before --activate. Backups and failed stages are kept.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

try:
    from .seed_guard import SeedGuard, fingerprint, require_unchanged
except ImportError:  # Direct script invocation.
    from seed_guard import SeedGuard, fingerprint, require_unchanged


def unused_path(path: Path) -> None:
    if os.path.lexists(path):
        raise FileExistsError(f"Refusing to overwrite {path}")


def activate(stage: Path, active: Path, backup: Path) -> Path | None:
    """Preserve the old database and restore it if stage activation fails."""
    if not stage.is_dir() or stage.is_symlink():
        raise ValueError(f"Staging database is not a regular directory: {stage}")
    if active.is_symlink() or (active.exists() and not active.is_dir()):
        raise ValueError(f"Active database is not a regular directory: {active}")
    unused_path(backup)
    saved = None
    if active.exists():
        active.rename(backup)
        saved = backup
    try:
        unused_path(active)
        stage.rename(active)
    except Exception:
        # Do not clobber a path created by a concurrent process.
        if saved is not None and not os.path.lexists(active):
            saved.rename(active)
        raise
    return saved


def rebuild(graph_dir: Path, *, activate_result: bool = False) -> Path:
    with SeedGuard(graph_dir / "seed.jsonl") as guard:
        return rebuild_locked(graph_dir, activate_result=activate_result, guard=guard)


def rebuild_locked(graph_dir: Path, *, activate_result: bool, guard: SeedGuard) -> Path:
    graph_dir = graph_dir.resolve()
    for name in ("readings.pg", "seed.jsonl", "readings.gq"):
        if not (graph_dir / name).is_file():
            raise FileNotFoundError(graph_dir / name)
    run_id = uuid.uuid4().hex
    workspace = graph_dir / f"readings.nano.build-{run_id}"
    stage = workspace / "database.nano"
    backup = graph_dir / f"readings.nano.backup-{run_id}"
    lock = graph_dir / "readings.nano.rebuild-lock"
    # Exclusive directory creation prevents two instances of this helper racing.
    # Other Nanograph clients still need to be stopped before activation.
    lock.mkdir()
    try:
        unused_path(workspace)
        workspace.mkdir()
        # Nanograph generates configuration beside the schema passed to init.
        # Use a disposable copy so no scaffold reaches repository sources.
        snapshots = {}
        for name in ("readings.pg", "seed.jsonl", "readings.gq"):
            source = graph_dir / name
            snapshots[name] = fingerprint(source)
            shutil.copyfile(source, workspace / name)
            require_unchanged(workspace / name, snapshots[name])
        staged_schema = workspace / "readings.pg"
        commands = (
            ("init", "--schema", str(staged_schema)),
            ("load", "--data", str(workspace / "seed.jsonl"), "--mode", "overwrite"),
            ("lint", "--query", str(workspace / "readings.gq")),
            ("doctor", "--schema", str(staged_schema), "--verbose"),
        )
        for command in commands:
            subprocess.run(
                ["nanograph", command[0], "--db", str(stage), *command[1:]],
                cwd=workspace,
                check=True,
            )
        guard.check()
        for name, expected in snapshots.items():
            require_unchanged(graph_dir / name, expected)
        if not activate_result:
            print(f"Validated staging database: {stage}")
            print("Active database unchanged. Use --activate to build and activate a fresh stage.")
            return stage
        saved = activate(stage, graph_dir / "readings.nano", backup)
        if saved is not None:
            print(f"Previous database preserved: {saved}")
        print(f"Active database: {graph_dir / 'readings.nano'}")
        return graph_dir / "readings.nano"
    except Exception:
        if workspace.exists():
            print(f"Staging artefacts retained: {workspace}", file=sys.stderr)
        raise
    finally:
        lock.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate", action="store_true",
                        help="activate the validated build and preserve any old database")
    args = parser.parse_args()
    try:
        rebuild(Path(__file__).resolve().parent, activate_result=args.activate)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Rebuild failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
