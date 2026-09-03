"""
INDIA AI TRADER V15.9
WALK-FORWARD / COST-AWARE VALIDATION

This is the research gate for V16.

A model does not get promoted because accuracy looks good.
It must survive chronological, out-of-sample evaluation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np


def strategy_returns(
    predictions,
    future_returns,
    transaction_cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
):

    predictions = np.asarray(
        predictions
    )

    future_returns = np.asarray(
        future_returns,
        dtype=float,
    )

    positions = np.where(
        predictions == 2,
        1,
        np.where(
            predictions == 0,
            -1,
            0,
        ),
    )

    executable = (
        positions != 0
    )

    costs = (
        transaction_cost_bps
        +
        slippage_bps
    ) / 10000.0

    returns = (
        positions *
        future_returns
    )

    returns = np.where(
        executable,
        returns - costs,
        0.0,
    )

    return returns


def calculate_metrics(
    returns: np.ndarray,
) -> Dict[str, Any]:

    active = returns[
        returns != 0
    ]

    if len(active) == 0:

        return {
            "trades":
                0,
            "win_rate":
                0.0,
            "net_return":
                0.0,
            "average_trade":
                0.0,
            "profit_factor":
                0.0,
            "max_drawdown":
                0.0,
            "expectancy":
                0.0,
        }

    wins = active[
        active > 0
    ]

    losses = active[
        active < 0
    ]

    gross_profit = float(
        wins.sum()
    )

    gross_loss = abs(
        float(
            losses.sum()
        )
    )

    equity = (
        1.0 +
        np.cumsum(
            returns
        )
    )

    running_peak = np.maximum.accumulate(
        equity
    )

    drawdown = (
        running_peak -
        equity
    )

    max_drawdown = float(
        drawdown.max()
    )

    return {
        "trades":
            int(len(active)),
        "win_rate":
            round(
                len(wins)
                / len(active)
                * 100,
                4,
            ),
        "net_return":
            round(
                float(
                    returns.sum()
                ),
                6,
            ),
        "average_trade":
            round(
                float(
                    active.mean()
                ),
                6,
            ),
        "profit_factor":
            (
                round(
                    gross_profit /
                    gross_loss,
                    4,
                )
                if gross_loss > 0
                else (
                    "inf"
                    if gross_profit > 0
                    else 0
                )
            ),
        "max_drawdown":
            round(
                max_drawdown,
                6,
            ),
        "expectancy":
            round(
                float(
                    active.mean()
                ),
                6,
            ),
    }


def walk_forward_evaluate(
    datasets: List[Dict[str, Any]],
    model_factory,
    feature_columns: List[str],
    folds: int = 5,
    transaction_cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
):

    fold_results = []

    for dataset in datasets:

        X = dataset["X"]
        y = dataset["y"]
        future_returns = dataset[
            "future_returns"
        ]

        n = len(X)

        if n < 500:
            continue

        minimum_train = int(
            n * 0.55
        )

        remaining = (
            n -
            minimum_train
        )

        test_size = max(
            1,
            remaining // folds,
        )

        for fold in range(
            folds
        ):

            train_end = (
                minimum_train
                +
                fold *
                test_size
            )

            test_start = train_end

            test_end = min(
                n,
                test_start +
                test_size,
            )

            if test_start >= n:
                break

            train_X = X.iloc[
                :train_end
            ]

            train_y = y.iloc[
                :train_end
            ]

            test_X = X.iloc[
                test_start:test_end
            ]

            test_y = y.iloc[
                test_start:test_end
            ]

            test_returns = (
                future_returns[
                    test_start:test_end
                ]
            )

            model = model_factory()

            model.fit(
                train_X,
                train_y,
            )

            predictions = (
                model.predict(
                    test_X[
                        feature_columns
                    ]
                )
            )

            returns = strategy_returns(
                predictions,
                test_returns,
                transaction_cost_bps,
                slippage_bps,
            )

            metrics = calculate_metrics(
                returns
            )

            fold_results.append({
                "dataset":
                    dataset.get(
                        "symbol"
                    ),
                "fold":
                    fold + 1,
                **metrics,
            })

    if not fold_results:

        return {
            "folds":
                [],
            "summary":
                {
                    "valid_folds":
                        0,
                },
        }

    numeric_fields = [
        "win_rate",
        "net_return",
        "average_trade",
        "max_drawdown",
        "expectancy",
    ]

    summary = {
        field:
            float(
                np.mean([
                    row[field]
                    for row
                    in fold_results
                ])
            )
        for field
        in numeric_fields
    }

    summary[
        "valid_folds"
    ] = len(
        fold_results
    )

    profitable_folds = sum(
        1
        for row
        in fold_results
        if row["net_return"] > 0
    )

    summary[
        "profitable_fold_ratio"
    ] = (
        profitable_folds
        /
        len(fold_results)
    )

    return {
        "folds":
            fold_results,
        "summary":
            summary,
    }


def promotion_gate(
    validation: Dict[str, Any],
) -> Dict[str, Any]:

    summary = validation.get(
        "summary",
        {},
    )

    valid_folds = int(
        summary.get(
            "valid_folds",
            0,
        )
    )

    profitable_ratio = float(
        summary.get(
            "profitable_fold_ratio",
            0,
        )
    )

    expectancy = float(
        summary.get(
            "expectancy",
            0,
        )
    )

    drawdown = float(
        summary.get(
            "max_drawdown",
            999,
        )
    )

    reasons = []

    if valid_folds < 3:
        reasons.append(
            "Insufficient walk-forward folds."
        )

    if profitable_ratio < 0.60:
        reasons.append(
            "Too few profitable out-of-sample folds."
        )

    if expectancy <= 0:
        reasons.append(
            "Out-of-sample expectancy is not positive."
        )

    if drawdown > 0.10:
        reasons.append(
            "Maximum drawdown exceeds 10%."
        )

    return {
        "promote":
            len(reasons) == 0,
        "reasons":
            reasons,
        "criteria":
            {
                "minimum_folds":
                    3,
                "minimum_profitable_fold_ratio":
                    0.60,
                "minimum_expectancy":
                    0,
                "maximum_drawdown":
                    0.10,
            },
    }