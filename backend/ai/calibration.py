"""
INDIA AI TRADER V15.7
PROBABILITY CALIBRATION

Calibrates V15 probabilities using resolved historical outcomes.

Calibration is intentionally separated from prediction.
"""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, List

import numpy as np


def _db_path():
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


def probability_band(
    probability: float,
) -> str:

    if probability < 50:
        return "<50"

    if probability < 55:
        return "50-55"

    if probability < 60:
        return "55-60"

    if probability < 65:
        return "60-65"

    if probability < 70:
        return "65-70"

    if probability < 75:
        return "70-75"

    return "75+"


def build_calibration_table():

    with _connection() as conn:

        rows = conn.execute(
            """
            SELECT
                signal,
                prediction_probability,
                direction_correct,
                return_30m
            FROM model_outcomes
            WHERE status = 'RESOLVED'
              AND prediction_probability IS NOT NULL
            """
        ).fetchall()

    buckets: Dict[str, List[float]] = {}

    for row in rows:

        probability = float(
            row["prediction_probability"]
        )

        band = probability_band(
            probability
        )

        buckets.setdefault(
            f"{row['signal']}:{band}",
            [],
        )

        if row["direction_correct"] is not None:

            buckets[
                f"{row['signal']}:{band}"
            ].append(
                float(
                    row["direction_correct"]
                )
            )

    result = {}

    for key, values in buckets.items():

        result[key] = {
            "observations":
                len(values),
            "empirical_accuracy":
                (
                    sum(values)
                    / len(values)
                    * 100
                    if values
                    else 0.0
                ),
        }

    return result


def calibrate_probability(
    signal: str,
    raw_probability: float,
) -> Dict[str, Any]:

    signal = signal.upper()

    raw_probability = float(
        raw_probability
    )

    table = build_calibration_table()

    band = probability_band(
        raw_probability
    )

    key = (
        f"{signal}:{band}"
    )

    bucket = table.get(
        key
    )

    if not bucket or bucket["observations"] < 20:

        return {
            "raw_probability":
                raw_probability,
            "calibrated_probability":
                raw_probability,
            "method":
                "IDENTITY",
            "band":
                band,
            "observations":
                bucket["observations"]
                if bucket
                else 0,
            "reliable":
                False,
        }

    empirical = float(
        bucket[
            "empirical_accuracy"
        ]
    )

    # Blend rather than fully overwrite.
    calibrated = (
        raw_probability * 0.5
        +
        empirical * 0.5
    )

    calibrated = max(
        0.0,
        min(
            100.0,
            calibrated,
        ),
    )

    return {
        "raw_probability":
            raw_probability,
        "calibrated_probability":
            calibrated,
        "method":
            "EMPIRICAL_BLEND",
        "band":
            band,
        "observations":
            bucket[
                "observations"
            ],
        "reliable":
            True,
    }