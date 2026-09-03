"""
INDIA AI TRADER V16
INTEGRATED INTELLIGENCE ENGINE

V16 combines:

- V15 XGBoost
- Probability calibration
- Outcome attribution
- Model registry
- Decision/risk integration

V16 does NOT automatically enable real trading.
Real money remains disabled.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai.calibration import (
    calibrate_probability,
)

from ai.outcome import (
    create_prediction_outcome,
    outcome_summary,
)

from ai.model_registry import (
    production_model,
)


# ============================================================
# CALIBRATE V15 OUTPUT
# ============================================================

def calibrate_model_output(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    result = dict(
        analysis
    )

    signal = str(
        result.get(
            "signal",
            "WAIT",
        )
    ).upper()

    probabilities = (
        result.get(
            "probabilities",
            result.get(
                "class_probabilities",
                {},
            ),
        )
        or {}
    )

    calibrated = {}

    for direction in (
        "BUY",
        "SELL",
        "WAIT",
    ):

        raw_probability = float(
            probabilities.get(
                direction,
                0.0,
            )
            or 0.0
        )

        try:

            calibration = (
                calibrate_probability(
                    direction,
                    raw_probability,
                )
            )

            calibrated[
                direction
            ] = float(
                calibration.get(
                    "calibrated_probability",
                    raw_probability,
                )
            )

        except Exception:

            calibrated[
                direction
            ] = raw_probability

    result[
        "calibrated_probabilities"
    ] = calibrated

    result[
        "production_model"
    ] = production_model()

    result[
        "v16_signal"
    ] = signal

    return result


# ============================================================
# CREATE OUTCOME RECORD
# ============================================================

def create_outcome_record(
    analysis: Dict[str, Any],
    signal_id: Optional[int] = None,
    trade_id: Optional[int] = None,
):

    signal = str(
        analysis.get(
            "signal",
            "WAIT",
        )
    ).upper()

    probabilities = (
        analysis.get(
            "probabilities",
            analysis.get(
                "class_probabilities",
                {},
            ),
        )
        or {}
    )

    probability = float(
        probabilities.get(
            signal,
            0.0,
        )
        or 0.0
    )

    entry = analysis.get(
        "entry"
    )

    if entry is None:

        entry = analysis.get(
            "latest_close"
        )

    try:

        entry = float(
            entry
        )

    except (
        TypeError,
        ValueError,
    ):

        entry = 0.0

    if entry <= 0:

        return None

    return create_prediction_outcome(
        signal_id=
            signal_id,

        symbol=
            str(
                analysis.get(
                    "symbol",
                    "UNKNOWN",
                )
            ).upper(),

        model_version=
            analysis.get(
                "model_version",
                "V15",
            ),

        signal=
            signal,

        prediction_probability=
            probability,

        entry_price=
            entry,

        trade_executed=
            trade_id is not None,

        trade_id=
            trade_id,
    )


# ============================================================
# V16 SUMMARY
# ============================================================

def v16_summary():

    return {
        "production_model":
            production_model(),

        "outcome_summary":
            outcome_summary(),

        "real_money":
            False,

        "paper_trading":
            True,
    }