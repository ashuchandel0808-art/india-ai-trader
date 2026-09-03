from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Optional


# ============================================================
# DATABASE LOCATION
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_DIR = PROJECT_ROOT

DATABASE_PATH = os.path.join(
    DATABASE_DIR,
    "trading.db",
)


# ============================================================
# CONNECTION
# ============================================================

def ensure_database_directory() -> None:
    os.makedirs(
        DATABASE_DIR,
        exist_ok=True,
    )


@contextmanager
def get_connection() -> Generator[
    sqlite3.Connection,
    None,
    None,
]:

    ensure_database_directory()

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    try:

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        yield connection

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database() -> None:

    ensure_database_directory()

    with get_connection() as connection:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # INSTRUMENTS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                exchange TEXT NOT NULL DEFAULT 'NSE',
                instrument_key TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # SIGNALS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,

                model_version TEXT NOT NULL,
                signal TEXT NOT NULL,

                buy_probability REAL NOT NULL DEFAULT 0,
                sell_probability REAL NOT NULL DEFAULT 0,
                wait_probability REAL NOT NULL DEFAULT 0,

                market_regime TEXT,

                entry REAL,
                stop_loss REAL,
                target_1 REAL,
                target_2 REAL,
                risk_reward REAL,

                decision TEXT,
                decision_reason TEXT,

                created_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # MODEL PREDICTIONS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS model_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                signal_id INTEGER,

                symbol TEXT NOT NULL,
                model_version TEXT NOT NULL,
                prediction TEXT NOT NULL,

                buy_probability REAL NOT NULL DEFAULT 0,
                sell_probability REAL NOT NULL DEFAULT 0,
                wait_probability REAL NOT NULL DEFAULT 0,

                features_hash TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY(signal_id)
                    REFERENCES signals(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ----------------------------------------------------
        # ORDERS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                signal_id INTEGER,

                symbol TEXT NOT NULL,
                side TEXT NOT NULL,

                quantity INTEGER NOT NULL,

                requested_price REAL,
                filled_price REAL,

                order_type TEXT NOT NULL DEFAULT 'PAPER',
                status TEXT NOT NULL,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(signal_id)
                    REFERENCES signals(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ----------------------------------------------------
        # POSITIONS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT NOT NULL,
                side TEXT NOT NULL,

                quantity INTEGER NOT NULL,
                average_price REAL NOT NULL,

                stop_loss REAL,
                target_price REAL,

                status TEXT NOT NULL DEFAULT 'OPEN',

                opened_at TEXT NOT NULL,
                closed_at TEXT
            )
            """
        )

        # ----------------------------------------------------
        # TRADES
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                order_id INTEGER,
                signal_id INTEGER,

                symbol TEXT NOT NULL,
                side TEXT NOT NULL,

                quantity INTEGER NOT NULL,

                entry_price REAL NOT NULL,
                exit_price REAL,

                stop_loss REAL,
                target_price REAL,

                pnl REAL,

                exit_reason TEXT,

                status TEXT NOT NULL DEFAULT 'OPEN',

                opened_at TEXT NOT NULL,
                closed_at TEXT,

                FOREIGN KEY(order_id)
                    REFERENCES orders(id)
                    ON DELETE SET NULL,

                FOREIGN KEY(signal_id)
                    REFERENCES signals(id)
                    ON DELETE SET NULL
            )
            """
        )

        # ----------------------------------------------------
        # PORTFOLIO SNAPSHOTS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT NOT NULL,

                cash REAL NOT NULL,
                invested REAL NOT NULL,
                market_value REAL NOT NULL,
                equity REAL NOT NULL,

                realized_pnl REAL NOT NULL DEFAULT 0,
                unrealized_pnl REAL NOT NULL DEFAULT 0
            )
            """
        )

        # ----------------------------------------------------
        # RISK EVENTS
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                timestamp TEXT NOT NULL,

                symbol TEXT,

                event TEXT NOT NULL,
                reason TEXT,

                risk_amount REAL,

                created_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_signals_symbol_time
            ON signals(symbol, timestamp)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_signals_model_time
            ON signals(model_version, created_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_predictions_symbol_time
            ON model_predictions(symbol, created_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_orders_symbol_time
            ON orders(symbol, created_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_trades_symbol_time
            ON trades(symbol, opened_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_positions_symbol_status
            ON positions(symbol, status)
            """
        )


# ============================================================
# SIGNAL PERSISTENCE
# ============================================================

def insert_signal(
    *,
    symbol: str,
    timestamp: str,
    model_version: str,
    signal: str,
    buy_probability: float,
    sell_probability: float,
    wait_probability: float,
    market_regime: Optional[str],
    entry: Optional[float],
    stop_loss: Optional[float],
    target_1: Optional[float],
    target_2: Optional[float],
    risk_reward: Optional[float],
    decision: Optional[str],
    decision_reason: Optional[str],
    created_at: str,
) -> int:

    initialize_database()

    with get_connection() as connection:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO signals (
                symbol,
                timestamp,
                model_version,
                signal,
                buy_probability,
                sell_probability,
                wait_probability,
                market_regime,
                entry,
                stop_loss,
                target_1,
                target_2,
                risk_reward,
                decision,
                decision_reason,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                symbol,
                timestamp,
                model_version,
                signal,
                float(
                    buy_probability or 0
                ),
                float(
                    sell_probability or 0
                ),
                float(
                    wait_probability or 0
                ),
                market_regime,
                entry,
                stop_loss,
                target_1,
                target_2,
                risk_reward,
                decision,
                decision_reason,
                created_at,
            ),
        )

        return int(
            cursor.lastrowid
        )


def insert_model_prediction(
    *,
    signal_id: Optional[int],
    symbol: str,
    model_version: str,
    prediction: str,
    buy_probability: float,
    sell_probability: float,
    wait_probability: float,
    features_hash: Optional[str],
    created_at: str,
) -> int:

    initialize_database()

    with get_connection() as connection:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO model_predictions (
                signal_id,
                symbol,
                model_version,
                prediction,
                buy_probability,
                sell_probability,
                wait_probability,
                features_hash,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                signal_id,
                symbol,
                model_version,
                prediction,
                float(
                    buy_probability or 0
                ),
                float(
                    sell_probability or 0
                ),
                float(
                    wait_probability or 0
                ),
                features_hash,
                created_at,
            ),
        )

        return int(
            cursor.lastrowid
        )


# ============================================================
# SIGNAL QUERIES
# ============================================================

def get_recent_signals(
    limit: int = 50,
):

    initialize_database()

    limit = max(
        1,
        min(
            int(limit),
            500,
        ),
    )

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_signal_count() -> int:

    initialize_database()

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM signals
            """
        ).fetchone()

        return int(
            row["count"]
        )


def get_prediction_count() -> int:

    initialize_database()

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM model_predictions
            """
        ).fetchone()

        return int(
            row["count"]
        )


# ============================================================
# DATABASE UTILITIES
# ============================================================

def database_exists() -> bool:

    return os.path.exists(
        DATABASE_PATH
    )


def database_path() -> str:

    return DATABASE_PATH


def get_table_names() -> list[str]:

    initialize_database()

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        return [
            row["name"]
            for row in rows
        ]


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print(
        "DATABASE INITIALIZED"
    )

    print(
        f"PATH: {DATABASE_PATH}"
    )

    print(
        "TABLES:"
    )

    for table in get_table_names():

        print(
            f"  - {table}"
        )

    print(
        "SIGNAL COUNT:",
        get_signal_count(),
    )

    print(
        "PREDICTION COUNT:",
        get_prediction_count(),
    )