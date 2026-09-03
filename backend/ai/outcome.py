"""
INDIA AI TRADER V15.6-H
OUTCOME ATTRIBUTION ENGINE

Records what happened after every model prediction,
whether or not a trade was executed.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _db_path() -> str:
    try:
        from database.db import database_path
        return database_path()
    except Exception:
        return (
            "/Users/ayushchandel/"
            "india-ai-trader-v5/database/"
            "trading.db"
        )


def _connection():
    connection = sqlite3.connect(
        _db_path()
    )
    connection.row_factory = sqlite3.Row
    return connection


def initialize_outcome_tables():
    with _connection() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                symbol TEXT NOT NULL,
                model_version TEXT,
                signal TEXT,
                prediction_probability REAL,
                entry_price REAL,
                return_5m REAL,
                return_15m REAL,
                return_30m REAL,
                return_60m REAL,
                max_favorable_return REAL,
                max_adverse_return REAL,
                direction_correct INTEGER,
                trade_executed INTEGER DEFAULT 0,
                trade_id INTEGER,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN'
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_model_outcomes_symbol
            ON model_outcomes(symbol)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_model_outcomes_signal
            ON model_outcomes(signal)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_model_outcomes_status
            ON model_outcomes(status)
            """
        )

        conn.commit()


def create_prediction_outcome(
    *,
    signal_id: Optional[int],
    symbol: str,
    model_version: str,
    signal: str,
    prediction_probability: Optional[float],
    entry_price: float,
    trade_executed: bool = False,
    trade_id: Optional[int] = None,
) -> int:

    initialize_outcome_tables()

    with _connection() as conn:

        cursor = conn.execute(
            """
            INSERT INTO model_outcomes (
                signal_id,
                symbol,
                model_version,
                signal,
                prediction_probability,
                entry_price,
                trade_executed,
                trade_id,
                created_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """,
            (
                signal_id,
                symbol.upper(),
                model_version,
                signal.upper(),
                prediction_probability,
                entry_price,
                1 if trade_executed else 0,
                trade_id,
                now_iso(),
            ),
        )

        conn.commit()

        return int(
            cursor.lastrowid
        )


def _calculate_return(
    entry: float,
    price: float,
    signal: str,
) -> float:

    if entry <= 0:
        return 0.0

    raw = (
        (price - entry)
        / entry
        * 100
    )

    if signal.upper() == "SELL":
        return -raw

    return raw


def resolve_prediction_outcome(
    outcome_id: int,
    *,
    price_5m: Optional[float] = None,
    price_15m: Optional[float] = None,
    price_30m: Optional[float] = None,
    price_60m: Optional[float] = None,
    max_favorable_price: Optional[float] = None,
    max_adverse_price: Optional[float] = None,
) -> Dict[str, Any]:

    initialize_outcome_tables()

    with _connection() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM model_outcomes
            WHERE id = ?
            """,
            (outcome_id,),
        ).fetchone()

        if row is None:
            raise ValueError(
                "Outcome record not found."
            )

        entry = float(
            row["entry_price"]
        )

        signal = str(
            row["signal"]
        ).upper()

        returns = {}

        for key, price in (
            ("5m", price_5m),
            ("15m", price_15m),
            ("30m", price_30m),
            ("60m", price_60m),
        ):

            returns[key] = (
                _calculate_return(
                    entry,
                    float(price),
                    signal,
                )
                if price is not None
                else None
            )

        favorable = None

        if max_favorable_price is not None:
            favorable = _calculate_return(
                entry,
                float(max_favorable_price),
                signal,
            )

        adverse = None

        if max_adverse_price is not None:
            adverse = _calculate_return(
                entry,
                float(max_adverse_price),
                signal,
            )

        reference_return = (
            returns["30m"]
            if returns["30m"] is not None
            else returns["15m"]
            if returns["15m"] is not None
            else returns["5m"]
        )

        direction_correct = None

        if reference_return is not None:

            direction_correct = (
                1
                if reference_return > 0
                else 0
            )

        conn.execute(
            """
            UPDATE model_outcomes
            SET
                return_5m = ?,
                return_15m = ?,
                return_30m = ?,
                return_60m = ?,
                max_favorable_return = ?,
                max_adverse_return = ?,
                direction_correct = ?,
                resolved_at = ?,
                status = 'RESOLVED'
            WHERE id = ?
            """,
            (
                returns["5m"],
                returns["15m"],
                returns["30m"],
                returns["60m"],
                favorable,
                adverse,
                direction_correct,
                now_iso(),
                outcome_id,
            ),
        )

        conn.commit()

        return {
            "outcome_id":
                outcome_id,
            "status":
                "RESOLVED",
            "returns":
                returns,
            "max_favorable_return":
                favorable,
            "max_adverse_return":
                adverse,
            "direction_correct":
                direction_correct,
        }


def get_open_outcomes():

    initialize_outcome_tables()

    with _connection() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM model_outcomes
            WHERE status = 'OPEN'
            ORDER BY created_at ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def outcome_summary():

    initialize_outcome_tables()

    with _connection() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM model_outcomes
            WHERE status = 'RESOLVED'
            """
        ).fetchall()

    if not rows:

        return {
            "count":
                0,
            "direction_accuracy":
                0.0,
            "average_5m":
                0.0,
            "average_15m":
                0.0,
            "average_30m":
                0.0,
            "average_60m":
                0.0,
            "average_mae":
                0.0,
            "average_mfe":
                0.0,
        }

    correct = [
        row["direction_correct"]
        for row in rows
        if row["direction_correct"] is not None
    ]

    def avg(column):
        values = [
            float(row[column])
            for row in rows
            if row[column] is not None
        ]
        return (
            sum(values) / len(values)
            if values
            else 0.0
        )

    return {
        "count":
            len(rows),
        "direction_accuracy":
            (
                sum(correct)
                / len(correct)
                * 100
                if correct
                else 0.0
            ),
        "average_5m":
            avg("return_5m"),
        "average_15m":
            avg("return_15m"),
        "average_30m":
            avg("return_30m"),
        "average_60m":
            avg("return_60m"),
        "average_mae":
            avg("max_adverse_return"),
        "average_mfe":
            avg("max_favorable_return"),
    }