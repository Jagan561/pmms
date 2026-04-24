"""
db_layer.py — SQLite database layer with WAL mode, connection pooling,
and improved error handling.
"""

import os
import sqlite3
import threading
from typing import Dict, List, Optional, Tuple


class DBLayer:
    """
    Thread-safe SQLite layer using a per-thread connection pool.
    WAL journal mode is enabled for better concurrent read/write performance.
    """

    def __init__(self, db_name: str = None):
        # Respect DB_PATH env var so Docker volume path is used automatically
        self.db_name = db_name or os.environ.get("DB_PATH", "memory_logs.db")
        os.makedirs(os.path.dirname(os.path.abspath(self.db_name)), exist_ok=True)
        self._local = threading.local()   # per-thread connection
        self._lock = threading.Lock()     # for DDL / bulk ops
        self._init_db()

    # ── Connection management ──────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Return (or create) a per-thread SQLite connection."""
        if not getattr(self._local, "conn", None):
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # WAL mode: readers don't block writers and vice-versa
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-8000")   # 8 MB page cache
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def close(self) -> None:
        """Close the current thread's connection."""
        c = getattr(self._local, "conn", None)
        if c:
            c.close()
            self._local.conn = None

    # ── Schema ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._lock:
            c = self._get_conn()
            c.executescript("""
                CREATE TABLE IF NOT EXISTS logs (
                    time          INTEGER,
                    process_id    TEXT,
                    memory_usage  INTEGER
                );

                CREATE TABLE IF NOT EXISTS system_memory_logs (
                    time      INTEGER PRIMARY KEY,
                    used_mb   INTEGER NOT NULL,
                    total_mb  INTEGER NOT NULL,
                    percent   REAL    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sml_time
                    ON system_memory_logs(time DESC);
            """)
            c.commit()
        self.seed_data()

    # ── Legacy demo API ───────────────────────────────────────────────────

    def insert_log(self, time: int, process_id: str, usage: int) -> None:
        c = self._get_conn()
        c.execute("INSERT INTO logs VALUES (?, ?, ?)", (time, process_id, usage))
        c.commit()

    def fetch_history(self) -> List[Tuple[int, str, int]]:
        c = self._get_conn()
        return c.execute(
            "SELECT time, process_id, memory_usage FROM logs"
        ).fetchall()

    # ── System memory API ─────────────────────────────────────────────────

    def upsert_system_snapshot(
        self, time: int, used_mb: int, total_mb: int, percent: float
    ) -> None:
        c = self._get_conn()
        c.execute(
            """
            INSERT INTO system_memory_logs(time, used_mb, total_mb, percent)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(time) DO UPDATE SET
                used_mb  = excluded.used_mb,
                total_mb = excluded.total_mb,
                percent  = excluded.percent
            """,
            (time, used_mb, total_mb, percent),
        )
        c.commit()

    def fetch_system_history(
        self, limit: Optional[int] = None
    ) -> List[Tuple[int, int]]:
        sql = "SELECT time, used_mb FROM system_memory_logs ORDER BY time ASC"
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        return self._get_conn().execute(sql, params).fetchall()

    def fetch_system_history_recent(
        self, limit: int = 300
    ) -> List[Tuple[int, int]]:
        rows = self._get_conn().execute(
            "SELECT time, used_mb FROM system_memory_logs ORDER BY time DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [(int(r["time"]), int(r["used_mb"])) for r in rows][::-1]

    def count_system_samples(self) -> int:
        row = self._get_conn().execute(
            "SELECT COUNT(*) AS n FROM system_memory_logs"
        ).fetchone()
        return int(row["n"])

    def clear_system_samples(self) -> None:
        c = self._get_conn()
        c.execute("DELETE FROM system_memory_logs")
        c.commit()

    def fetch_latest_system_snapshot(self) -> Optional[dict]:
        row = self._get_conn().execute(
            """SELECT time, used_mb, total_mb, percent
               FROM system_memory_logs ORDER BY time DESC LIMIT 1"""
        ).fetchone()
        if not row:
            return None
        return {
            "time":     int(row["time"]),
            "used_mb":  int(row["used_mb"]),
            "total_mb": int(row["total_mb"]),
            "percent":  float(row["percent"]),
        }

    def fetch_system_grouped_for_chart(
        self,
    ) -> Dict[str, List[Tuple[int, int]]]:
        rows = self._get_conn().execute(
            "SELECT time, used_mb FROM system_memory_logs ORDER BY time ASC"
        ).fetchall()
        return {"SYSTEM_RAM_MB": [(int(r["time"]), int(r["used_mb"])) for r in rows]}

    def fetch_system_rows_for_table(self, limit: int = 200) -> List[dict]:
        rows = self._get_conn().execute(
            """SELECT time, used_mb, total_mb, percent
               FROM system_memory_logs ORDER BY time DESC LIMIT ?""",
            (int(limit),),
        ).fetchall()
        return [
            {
                "time":     int(r["time"]),
                "process":  "SYSTEM",
                "usage":    int(r["used_mb"]),
                "total_mb": int(r["total_mb"]),
                "percent":  float(r["percent"]),
            }
            for r in rows
        ][::-1]

    # ── Seed ──────────────────────────────────────────────────────────────

    def seed_data(self) -> None:
        if not self.fetch_history():
            for t in range(1, 6):
                self.insert_log(t, "P1", 100 + t * 20)
                self.insert_log(t, "P2", 80 + t * 15)
                self.insert_log(t, "P3", 60 + t * 10)
