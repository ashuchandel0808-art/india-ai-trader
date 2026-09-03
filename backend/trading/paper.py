"""
INDIA AI TRADER V15.6-E
PAPER EXECUTION ENGINE

Flow
----
Decision
    ↓
Risk approval
    ↓
Paper order
    ↓
SQLite order record
    ↓
SQLite position record
    ↓
SQLite trade record

REAL MONEY:
-----------
Never used by this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import sqlite3

from database.db import (
    get_connection,
)


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def execute_paper_trade(
    *,
    symbol: str,
    side: str,
    quantity: int,
    entry_price: float,
    stop_loss: Optional[float],
    target_price: Optional[float],
    signal_id: Optional[int],
    portfolio: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a paper trade only.

    The caller must already have passed
    the decision/risk engine.
    """

    symbol = (
        symbol
        .strip()
        .upper()
    )

    side = (
        side
        .strip()
        .upper()
    )

    quantity = safe_int(
        quantity
    )

    entry_price = safe_float(
        entry_price
    )

    if side not in {
        "BUY",
        "SELL",
    }:

        raise ValueError(
            "Side must be BUY or SELL."
        )

    if quantity <= 0:

        raise ValueError(
            "Quantity must be positive."
        )

    if entry_price <= 0:

        raise ValueError(
            "Entry price must be positive."
        )

    cash = safe_float(
        portfolio.get(
            "cash",
            0,
        )
    )

    notional = (
        entry_price *
        quantity
    )

    # --------------------------------------------------------
    # PAPER CASH CHECK
    # --------------------------------------------------------

    if side == "BUY":

        if notional > cash:

            raise ValueError(
                (
                    "Insufficient paper "
                    f"cash. Required ₹{notional:,.2f}, "
                    f"available ₹{cash:,.2f}."
                )
            )

        portfolio[
            "cash"
        ] = cash - notional

    else:

        # Short-paper model:
        # proceeds are credited here.
        portfolio[
            "cash"
        ] = cash + notional

    created_at = now_iso()

    with get_connection() as connection:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO orders (
                signal_id,
                symbol,
                side,
                quantity,
                requested_price,
                filled_price,
                order_type,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                symbol,
                side,
                quantity,
                entry_price,
                entry_price,
                "PAPER",
                "FILLED",
                created_at,
                created_at,
            ),
        )

        order_id = int(
            cursor.lastrowid
        )

        # ----------------------------------------------------
        # POSITION
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                quantity,
                average_price,
                stop_loss,
                target_price
            FROM positions
            WHERE symbol = ?
              AND side = ?
              AND status = 'OPEN'
            LIMIT 1
            """,
            (
                symbol,
                side,
            ),
        )

        existing = cursor.fetchone()

        if existing:

            old_quantity = safe_int(
                existing[
                    "quantity"
                ]
            )

            old_average = safe_float(
                existing[
                    "average_price"
                ]
            )

            new_quantity = (
                old_quantity +
                quantity
            )

            new_average = (
                (
                    old_average *
                    old_quantity
                )
                +
                (
                    entry_price *
                    quantity
                )
            ) / new_quantity

            cursor.execute(
                """
                UPDATE positions
                SET
                    quantity = ?,
                    average_price = ?,
                    stop_loss = ?,
                    target_price = ?
                WHERE id = ?
                """,
                (
                    new_quantity,
                    new_average,
                    stop_loss,
                    target_price,
                    existing["id"],
                ),
            )

            position_id = int(
                existing["id"]
            )

        else:

            cursor.execute(
                """
                INSERT INTO positions (
                    symbol,
                    side,
                    quantity,
                    average_price,
                    stop_loss,
                    target_price,
                    status,
                    opened_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    side,
                    quantity,
                    entry_price,
                    stop_loss,
                    target_price,
                    "OPEN",
                    created_at,
                ),
            )

            position_id = int(
                cursor.lastrowid
            )

        # ----------------------------------------------------
        # TRADE
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO trades (
                order_id,
                signal_id,
                symbol,
                side,
                quantity,
                entry_price,
                exit_price,
                stop_loss,
                target_price,
                pnl,
                exit_reason,
                status,
                opened_at,
                closed_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                order_id,
                signal_id,
                symbol,
                side,
                quantity,
                entry_price,
                None,
                stop_loss,
                target_price,
                None,
                None,
                "OPEN",
                created_at,
                None,
            ),
        )

        trade_id = int(
            cursor.lastrowid
        )

    return {
        "status":
            "success",
        "execution_mode":
            "PAPER",
        "real_order_sent":
            False,
        "order_id":
            order_id,
        "position_id":
            position_id,
        "trade_id":
            trade_id,
        "symbol":
            symbol,
        "side":
            side,
        "quantity":
            quantity,
        "entry_price":
            entry_price,
        "stop_loss":
            stop_loss,
        "target_price":
            target_price,
        "notional":
            notional,
        "status":
            "FILLED",
        "timestamp":
            created_at,
    }


def close_paper_trade_db(
    trade_id: int,
    exit_price: float,
    exit_reason: str,
    portfolio: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Close a database-backed paper trade.
    """

    exit_price = safe_float(
        exit_price
    )

    if exit_price <= 0:

        raise ValueError(
            "Exit price must be positive."
        )

    with get_connection() as connection:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM trades
            WHERE id = ?
            LIMIT 1
            """,
            (
                trade_id,
            ),
        )

        trade = cursor.fetchone()

        if trade is None:

            raise ValueError(
                "Paper trade not found."
            )

        if trade["status"] != "OPEN":

            raise ValueError(
                "Paper trade is already closed."
            )

        quantity = safe_int(
            trade["quantity"]
        )

        entry_price = safe_float(
            trade["entry_price"]
        )

        side = str(
            trade["side"]
        ).upper()

        if side == "BUY":

            pnl = (
                exit_price -
                entry_price
            ) * quantity

            settlement = (
                exit_price *
                quantity
            )

            portfolio[
                "cash"
            ] += settlement

        else:

            pnl = (
                entry_price -
                exit_price
            ) * quantity

            cost_to_cover = (
                exit_price *
                quantity
            )

            portfolio[
                "cash"
            ] -= cost_to_cover

        closed_at = now_iso()

        cursor.execute(
            """
            UPDATE trades
            SET
                exit_price = ?,
                pnl = ?,
                exit_reason = ?,
                status = 'CLOSED',
                closed_at = ?
            WHERE id = ?
            """,
            (
                exit_price,
                pnl,
                exit_reason,
                closed_at,
                trade_id,
            ),
        )

        cursor.execute(
            """
            SELECT
                id,
                quantity
            FROM positions
            WHERE symbol = ?
              AND side = ?
              AND status = 'OPEN'
            LIMIT 1
            """,
            (
                trade["symbol"],
                side,
            ),
        )

        position = cursor.fetchone()

        if position:

            remaining = (
                safe_int(
                    position["quantity"]
                )
                -
                quantity
            )

            if remaining > 0:

                cursor.execute(
                    """
                    UPDATE positions
                    SET quantity = ?
                    WHERE id = ?
                    """,
                    (
                        remaining,
                        position["id"],
                    ),
                )

            else:

                cursor.execute(
                    """
                    UPDATE positions
                    SET
                        quantity = 0,
                        status = 'CLOSED',
                        closed_at = ?
                    WHERE id = ?
                    """,
                    (
                        closed_at,
                        position["id"],
                    ),
                )

    return {
        "status":
            "success",
        "execution_mode":
            "PAPER",
        "trade_id":
            trade_id,
        "symbol":
            trade["symbol"],
        "side":
            side,
        "quantity":
            quantity,
        "entry_price":
            entry_price,
        "exit_price":
            exit_price,
        "realized_pnl":
            round(
                pnl,
                2,
            ),
        "exit_reason":
            exit_reason,
        "status":
            "CLOSED",
        "timestamp":
            closed_at,
    }


def get_open_database_trades():

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM trades
            WHERE status = 'OPEN'
            ORDER BY opened_at DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def get_database_trade(
    trade_id: int,
):

    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT *
            FROM trades
            WHERE id = ?
            LIMIT 1
            """,
            (
                trade_id,
            ),
        ).fetchone()

        if row is None:
            return None

        return dict(row)