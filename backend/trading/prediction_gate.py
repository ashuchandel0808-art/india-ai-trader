"""
INDIA AI TRADER V16
PREDICTION INTEGRITY / DEDUPLICATION GATE

Prevents repeated API polling from creating duplicate
predictions for the same symbol and model candle.

Default behavior:
- One prediction per symbol per 5-minute bucket.
- BUY / SELL / WAIT are all deduplicated.
- A new prediction is allowed when the next 5-minute
  bucket begins.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def _db_path() -> str:

    try:

        from database.db import database_path

        return database_path()

    except Exception:

        return (
            "/Users/ayushchandel/"
            "india-ai-trader-v5/"
            "database/trading.db"
        )


def _connect():

    conn = sqlite3.connect(
        _db_path()
    )

    conn.row_factory = sqlite3.Row

    return conn


def initialize_prediction_gate():

    with _connect() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_gate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,

                model_version TEXT NOT NULL,

                interval_minutes INTEGER NOT NULL,

                candle_bucket INTEGER NOT NULL,

                prediction_id INTEGER,

                signal_id INTEGER,

                created_at TEXT NOT NULL,

                UNIQUE(
                    symbol,
                    model_version,
                    interval_minutes,
                    candle_bucket
                )
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_prediction_gate_lookup
            ON prediction_gate(
                symbol,
                model_version,
                interval_minutes,
                candle_bucket
            )
            """
        )

        conn.commit()


def candle_bucket(
    timestamp: Optional[str] = None,
    interval_minutes: int = 5,
) -> int:

    interval_seconds = (
        int(interval_minutes) * 60
    )

    if timestamp:

        try:

            value = str(
                timestamp
            ).strip()

            if value.endswith("Z"):

                value = (
                    value[:-1]
                    + "+00:00"
                )

            dt = datetime.fromisoformat(
                value
            )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            epoch = int(
                dt.timestamp()
            )

        except Exception:

            epoch = int(
                datetime.now(
                    timezone.utc
                ).timestamp()
            )

    else:

        epoch = int(
            datetime.now(
                timezone.utc
            ).timestamp()
        )

    return (
        epoch //
        interval_seconds
    )


def claim_prediction_slot(
    symbol: str,
    model_version: str,
    interval_minutes: int = 5,
    candle_timestamp: Optional[str] = None,
):

    initialize_prediction_gate()

    bucket = candle_bucket(
        candle_timestamp,
        interval_minutes,
    )

    clean_symbol = (
        str(symbol)
        .strip()
        .upper()
    )

    clean_model = (
        str(model_version)
        .strip()
        .upper()
    )

    created_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )

    with _connect() as conn:

        try:

            cursor = conn.execute(
                """
                INSERT INTO prediction_gate (
                    symbol,
                    model_version,
                    interval_minutes,
                    candle_bucket,
                    prediction_id,
                    signal_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, NULL, NULL, ?)
                """,
                (
                    clean_symbol,
                    clean_model,
                    int(
                        interval_minutes
                    ),
                    int(bucket),
                    created_at,
                ),
            )

            conn.commit()

            return {
                "allowed":
                    True,
                "reason":
                    "NEW_CANDLE",
                "bucket":
                    bucket,
                "gate_id":
                    cursor.lastrowid,
            }

        except sqlite3.IntegrityError:

            row = conn.execute(
                """
                SELECT
                    id,
                    prediction_id,
                    signal_id,
                    created_at
                FROM prediction_gate
                WHERE
                    symbol = ?
                    AND model_version = ?
                    AND interval_minutes = ?
                    AND candle_bucket = ?
                LIMIT 1
                """,
                (
                    clean_symbol,
                    clean_model,
                    int(
                        interval_minutes
                    ),
                    int(bucket),
                ),
            ).fetchone()

            return {
                "allowed":
                    False,
                "reason":
                    "DUPLICATE_CANDLE",
                "bucket":
                    bucket,
                "gate_id":
                    (
                        row["id"]
                        if row
                        else None
                    ),
                "prediction_id":
                    (
                        row["prediction_id"]
                        if row
                        else None
                    ),
                "signal_id":
                    (
                        row["signal_id"]
                        if row
                        else None
                    ),
            }


def attach_prediction(
    gate_id: int,
    prediction_id=None,
    signal_id=None,
):

    initialize_prediction_gate()

    with _connect() as conn:

        conn.execute(
            """
            UPDATE prediction_gate
            SET
                prediction_id = ?,
                signal_id = ?
            WHERE id = ?
            """,
            (
                prediction_id,
                signal_id,
                int(gate_id),
            ),
        )

        conn.commit()


def gate_status():

    initialize_prediction_gate()

    with _connect() as conn:

        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM prediction_gate
            """
        ).fetchone()[0]

        today = conn.execute(
            """
            SELECT COUNT(*)
            FROM prediction_gate
            WHERE
                created_at >= ?
            """,
            (
                datetime.now(
                    timezone.utc
                )
                .replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                .isoformat(),
            ),
        ).fetchone()[0]

    return {
        "status":
            "success",
        "total_slots":
            total,
        "today_slots":
            today,
    }