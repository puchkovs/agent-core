"""Transactional snapshots, operation outcomes, artifacts and event cursors."""

from __future__ import annotations

import fcntl
import os
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .contracts import TRANSITIONS, CoreError, Event, Json, Operation, Run, canonical, digest


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(self.path, 0o600)
        self.connection = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1}:
            self.close()
            raise CoreError("unsupported_store_version")
        if version == 0:
            self.connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                    body TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS operations(
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, timestamp REAL NOT NULL, operation_id TEXT,
                    body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_by_run ON events(run_id, seq);
                CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                PRAGMA user_version=1;
                COMMIT;
            """)
        os.chmod(self.path, 0o600)

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    @contextmanager
    def driver(self, run_id: str) -> Iterator[None]:
        # Hash untrusted identifiers before using them in filesystem paths.
        lock = self.path.with_name(self.path.name + "." + digest(run_id) + ".lockfile")
        with lock.open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CoreError("run_busy") from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def create(self, run: Run) -> None:
        with self.transaction():
            self.connection.execute(
                "INSERT OR IGNORE INTO sessions VALUES (?,?)",
                (run.session_id, time.time()),
            )
            self.connection.execute(
                "INSERT INTO runs(id,session_id,body) VALUES (?,?,?)",
                (run.id, run.session_id, run.model_dump_json()),
            )
            self._event(run.id, "run.created", None, {})

    def load(self, run_id: str) -> Run:
        row = self.connection.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise CoreError("unknown_run")
        return Run.model_validate_json(row[0])

    def operation(self, operation_id: str) -> Operation | None:
        row = self.connection.execute(
            "SELECT body FROM operations WHERE id=?",
            (operation_id,),
        ).fetchone()
        return None if row is None else Operation.model_validate_json(row[0])

    def operations(self, run_id: str) -> tuple[Operation, ...]:
        return tuple(
            Operation.model_validate_json(row[0])
            for row in self.connection.execute(
                "SELECT body FROM operations WHERE run_id=? ORDER BY rowid",
                (run_id,),
            )
        )

    def _event(
        self, run_id: str, kind: str, operation_id: str | None, data: dict[str, Json]
    ) -> None:
        self.connection.execute(
            "INSERT INTO events(run_id,kind,timestamp,operation_id,body) VALUES (?,?,?,?,?)",
            (run_id, kind, time.time(), operation_id, canonical(data)),
        )

    def save(
        self,
        run: Run,
        kind: str,
        operation: Operation | None = None,
        data: dict[str, Json] | None = None,
    ) -> None:
        with self.transaction():
            previous = self.load(run.id)
            if previous.status != run.status and run.status not in TRANSITIONS.get(
                previous.status, set()
            ):
                raise CoreError("invalid_transition")
            if kind == "tool.dispatched" and self.cancelled(run.id):
                raise CoreError("cancelled")
            self.connection.execute(
                "UPDATE runs SET body=? WHERE id=?", (run.model_dump_json(), run.id)
            )
            if operation is not None:
                self.connection.execute(
                    "INSERT INTO operations VALUES (?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                    (operation.id, operation.run_id, operation.model_dump_json()),
                )
            self._event(run.id, kind, None if operation is None else operation.id, data or {})

    def cancelled(self, run_id: str) -> bool:
        row = self.connection.execute("SELECT cancelled FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise CoreError("unknown_run")
        return bool(row[0])

    def cancel(self, run_id: str) -> None:
        with self.transaction():
            run = self.load(run_id)
            if not run.status.terminal and not self.cancelled(run_id):
                self.connection.execute("UPDATE runs SET cancelled=1 WHERE id=?", (run_id,))
                self._event(run_id, "run.cancel_requested", None, {})

    def decide(
        self,
        run_id: str,
        operation_id: str,
        binding: str,
        actor: str,
        allow: bool,
    ) -> None:
        if not actor.strip():
            raise CoreError("invalid_actor")
        with self.transaction():
            run = self.load(run_id)
            operation = self.operation(operation_id)
            if (
                operation is None
                or operation.run_id != run_id
                or run.status.value != "waiting_approval"
                or operation.status != "prepared"
                or operation.approval is not None
                or operation.binding != binding
                or operation.expires_at is None
                or time.time() >= operation.expires_at
            ):
                raise CoreError("invalid_approval")
            updated = operation.model_copy(
                update={"approval": "allow" if allow else "deny", "actor": actor}
            )
            self.connection.execute(
                "UPDATE operations SET body=? WHERE id=?",
                (updated.model_dump_json(), operation_id),
            )
            self._event(run_id, "approval.decided", operation_id, {"allow": allow, "actor": actor})

    def events(self, run_id: str, after: int = 0, limit: int = 100) -> tuple[Event, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("event page must contain 1..1000 entries")
        return tuple(
            Event(
                sequence=row[0],
                run_id=run_id,
                kind=row[1],
                timestamp=row[2],
                operation_id=row[3],
                data=__import__("json").loads(row[4]),
            )
            for row in self.connection.execute(
                "SELECT seq,kind,timestamp,operation_id,body FROM events "
                "WHERE run_id=? AND seq>? ORDER BY seq LIMIT ?",
                (run_id, after, limit),
            )
        )

    def artifact(self, text: str) -> str:
        key = digest(text)
        self.connection.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?)", (key, text))
        return key

    def read_artifact(self, key: str, offset: int = 0, limit: int = 4096) -> str:
        if offset < 0 or not 1 <= limit <= 65536:
            raise ValueError("invalid artifact range")
        row = self.connection.execute("SELECT body FROM artifacts WHERE id=?", (key,)).fetchone()
        if row is None:
            raise CoreError("unknown_artifact")
        return str(row[0])[offset : offset + limit]
