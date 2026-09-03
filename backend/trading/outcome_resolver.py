"""
INDIA AI TRADER V16
AUTOMATIC OUTCOME RESOLVER

Purpose
-------
Automatically observes what happened after every saved
model prediction.

Milestones
----------
5 minutes
15 minutes
30 minutes
60 minutes

The resolver stores milestone prices in a separate table and
only marks the model outcome RESOLVED after the 60-minute
observation is available.

This works for:
    BUY
    SELL

WAIT predictions are retained but are not treated as
directional trades.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ============================================================
# DATABASE
# ============================================================

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

    connection.row_factory = (
        sqlite3.Row
    )

    return connection


# ============================================================
# TIME
# ============================================================

def now_utc() -> datetime:

    return datetime.now(
        timezone.utc
    )


def parse_timestamp(
    value: Any,
) -> Optional[datetime]:

    if not value:
        return None

    try:

        text = str(
            value
        ).strip()

        if text.endswith("Z"):

            text = (
                text[:-1]
                + "+00:00"
            )

        parsed = datetime.fromisoformat(
            text
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except Exception:

        return None


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_resolver_table():

    with _connection() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcome_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                outcome_id INTEGER NOT NULL UNIQUE,

                symbol TEXT NOT NULL,

                signal TEXT NOT NULL,

                entry_price REAL NOT NULL,

                created_at TEXT NOT NULL,

                price_5m REAL,

                price_15m REAL,

                price_30m REAL,

                price_60m REAL,

                checked_5m INTEGER NOT NULL DEFAULT 0,

                checked_15m INTEGER NOT NULL DEFAULT 0,

                checked_30m INTEGER NOT NULL DEFAULT 0,

                checked_60m INTEGER NOT NULL DEFAULT 0,

                resolved INTEGER NOT NULL DEFAULT 0,

                last_checked_at TEXT

            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_outcome_observations_resolved
            ON outcome_observations(resolved)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_outcome_observations_created
            ON outcome_observations(created_at)
            """
        )

        conn.commit()


# ============================================================
# REGISTER OUTCOME
# ============================================================

def register_outcome(
    outcome_id: int,
    symbol: str,
    signal: str,
    entry_price: float,
    created_at: str,
):

    initialize_resolver_table()

    with _connection() as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO outcome_observations (
                outcome_id,
                symbol,
                signal,
                entry_price,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                int(outcome_id),
                str(symbol).upper(),
                str(signal).upper(),
                float(entry_price),
                created_at,
            ),
        )

        conn.commit()


# ============================================================
# SYNC OPEN OUTCOMES
# ============================================================

def sync_open_outcomes():

    initialize_resolver_table()

    try:

        from ai.outcome import (
            get_open_outcomes,
        )

        outcomes = (
            get_open_outcomes()
        )

    except Exception as exc:

        return {
            "status":
                "error",
            "message":
                "Unable to read open outcomes.",
            "error":
                str(exc),
            "registered":
                0,
        }

    registered = 0

    with _connection() as conn:

        for outcome in outcomes:

            outcome_id = outcome.get(
                "id"
            )

            if outcome_id is None:
                continue

            symbol = outcome.get(
                "symbol"
            )

            signal = outcome.get(
                "signal",
                "WAIT",
            )

            entry_price = outcome.get(
                "entry_price"
            )

            created_at = outcome.get(
                "created_at"
            )

            if (
                not symbol
                or entry_price is None
                or not created_at
            ):
                continue

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO outcome_observations (
                    outcome_id,
                    symbol,
                    signal,
                    entry_price,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(outcome_id),
                    str(symbol).upper(),
                    str(signal).upper(),
                    float(entry_price),
                    str(created_at),
                ),
            )

            if cursor.rowcount > 0:

                registered += 1

        conn.commit()

    return {
        "status":
            "success",
        "registered":
            registered,
        "open_outcomes":
            len(outcomes),
    }


# ============================================================
# OPEN OBSERVATIONS
# ============================================================

def get_pending_observations():

    initialize_resolver_table()

    with _connection() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM outcome_observations
            WHERE resolved = 0
            ORDER BY created_at ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ============================================================
# UPDATE MILESTONE
# ============================================================

def _update_milestone(
    outcome_id: int,
    milestone: str,
    price: float,
):

    allowed = {
        "5m":
            (
                "price_5m",
                "checked_5m",
            ),
        "15m":
            (
                "price_15m",
                "checked_15m",
            ),
        "30m":
            (
                "price_30m",
                "checked_30m",
            ),
        "60m":
            (
                "price_60m",
                "checked_60m",
            ),
    }

    if milestone not in allowed:

        raise ValueError(
            f"Unsupported milestone: {milestone}"
        )

    price_column, checked_column = (
        allowed[milestone]
    )

    with _connection() as conn:

        conn.execute(
            f"""
            UPDATE outcome_observations
            SET
                {price_column} = ?,
                {checked_column} = 1,
                last_checked_at = ?
            WHERE outcome_id = ?
            """,
            (
                float(price),
                now_utc().isoformat(),
                int(outcome_id),
            ),
        )

        conn.commit()


# ============================================================
# RESOLVE FINAL OUTCOME
# ============================================================

def _resolve_if_ready(
    observation: Dict[str, Any],
):

    if not observation.get(
        "price_60m"
    ):
        return {
            "resolved":
                False,
            "reason":
                "60-minute observation not available.",
        }

    try:

        from ai.outcome import (
            resolve_prediction_outcome,
        )

        result = (
            resolve_prediction_outcome(
                int(
                    observation[
                        "outcome_id"
                    ]
                ),

                price_5m=
                    observation.get(
                        "price_5m"
                    ),

                price_15m=
                    observation.get(
                        "price_15m"
                    ),

                price_30m=
                    observation.get(
                        "price_30m"
                    ),

                price_60m=
                    observation.get(
                        "price_60m"
                    ),

                max_favorable_price=
                    _calculate_mfe_price(
                        observation
                    ),

                max_adverse_price=
                    _calculate_mae_price(
                        observation
                    ),
            )
        )

    except Exception as exc:

        return {
            "resolved":
                False,
            "reason":
                "Outcome resolution failed.",
            "error":
                str(exc),
        }

    with _connection() as conn:

        conn.execute(
            """
            UPDATE outcome_observations
            SET
                resolved = 1,
                last_checked_at = ?
            WHERE outcome_id = ?
            """,
            (
                now_utc().isoformat(),
                int(
                    observation[
                        "outcome_id"
                    ]
                ),
            ),
        )

        conn.commit()

    return {
        "resolved":
            True,
        "result":
            result,
    }


# ============================================================
# MFE / MAE
# ============================================================

def _calculate_mfe_price(
    observation: Dict[str, Any],
) -> Optional[float]:

    prices = []

    for key in (
        "price_5m",
        "price_15m",
        "price_30m",
        "price_60m",
    ):

        value = observation.get(
            key
        )

        if value is not None:

            prices.append(
                float(value)
            )

    if not prices:
        return None

    signal = str(
        observation.get(
            "signal",
            "WAIT",
        )
    ).upper()

    if signal == "SELL":

        return min(prices)

    return max(prices)


def _calculate_mae_price(
    observation: Dict[str, Any],
) -> Optional[float]:

    prices = []

    for key in (
        "price_5m",
        "price_15m",
        "price_30m",
        "price_60m",
    ):

        value = observation.get(
            key
        )

        if value is not None:

            prices.append(
                float(value)
            )

    if not prices:
        return None

    signal = str(
        observation.get(
            "signal",
            "WAIT",
        )
    ).upper()

    if signal == "SELL":

        return max(prices)

    return min(prices)


# ============================================================
# RESOLVER
# ============================================================

def resolve_pending(
    get_price,
    max_items: int = 50,
):

    initialize_resolver_table()

    sync_result = (
        sync_open_outcomes()
    )

    observations = (
        get_pending_observations()
    )

    processed = 0
    milestones_updated = 0
    resolved = 0
    skipped = 0
    errors = []

    current_time = now_utc()

    for observation in observations[
        :max_items
    ]:

        created = parse_timestamp(
            observation.get(
                "created_at"
            )
        )

        if created is None:

            skipped += 1
            continue

        elapsed_seconds = (
            current_time -
            created
        ).total_seconds()

        signal = str(
            observation.get(
                "signal",
                "WAIT",
            )
        ).upper()

        symbol = str(
            observation.get(
                "symbol",
                "",
            )
        ).upper()

        if not symbol:

            skipped += 1
            continue

        # --------------------------------------------
        # WAIT predictions are still useful as
        # observations, but there is no directional
        # MFE/MAE interpretation required.
        # --------------------------------------------

        milestones = [
            (
                "5m",
                300,
                "checked_5m",
            ),
            (
                "15m",
                900,
                "checked_15m",
            ),
            (
                "30m",
                1800,
                "checked_30m",
            ),
            (
                "60m",
                3600,
                "checked_60m",
            ),
        ]

        for milestone, required_seconds, flag in milestones:

            if elapsed_seconds < required_seconds:

                continue

            if observation.get(
                flag
            ):

                continue

            try:

                price = get_price(
                    symbol
                )

                if price is None:

                    continue

                _update_milestone(
                    int(
                        observation[
                            "outcome_id"
                        ]
                    ),
                    milestone,
                    float(price),
                )

                observation[
                    f"price_{milestone}"
                ] = float(price)

                observation[
                    flag
                ] = 1

                milestones_updated += 1

                processed += 1

            except Exception as exc:

                errors.append({
                    "outcome_id":
                        observation.get(
                            "outcome_id"
                        ),
                    "symbol":
                        symbol,
                    "milestone":
                        milestone,
                    "error":
                        str(exc),
                })

        # Reload row after updates.
        with _connection() as conn:

            row = conn.execute(
                """
                SELECT *
                FROM outcome_observations
                WHERE outcome_id = ?
                """,
                (
                    int(
                        observation[
                            "outcome_id"
                        ]
                    ),
                ),
            ).fetchone()

        if row is None:
            continue

        refreshed = dict(row)

        final_result = _resolve_if_ready(
            refreshed
        )

        if final_result.get(
            "resolved"
        ):

            resolved += 1

    return {
        "status":
            "success",

        "sync":
            sync_result,

        "observations_scanned":
            len(observations),

        "processed":
            processed,

        "milestones_updated":
            milestones_updated,

        "resolved":
            resolved,

        "skipped":
            skipped,

        "errors":
            errors,

        "timestamp":
            now_utc().isoformat(),
    }


# ============================================================
# STATUS
# ============================================================

def resolver_status():

    initialize_resolver_table()

    with _connection() as conn:

        total = conn.execute(
            """
            SELECT COUNT(*)
            FROM outcome_observations
            """
        ).fetchone()[0]

        open_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM outcome_observations
            WHERE resolved = 0
            """
        ).fetchone()[0]

        resolved_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM outcome_observations
            WHERE resolved = 1
            """
        ).fetchone()[0]

    return {
        "status":
            "success",
        "total_observations":
            total,
        "open_observations":
            open_count,
        "resolved_observations":
            resolved_count,
        "timestamp":
            now_utc().isoformat(),
    }