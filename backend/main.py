"""
INDIA AI TRADER V16
INTEGRATED AI TRADING RESEARCH + PAPER TRADING BACKEND

PIPELINE
--------
Upstox
  ↓
Live market data
  ↓
V15 XGBoost
  ↓
Probability calibration
  ↓
Prediction Integrity Gate
  ↓
Decision engine
  ↓
Risk engine
  ↓
Paper execution
  ↓
SQLite
  ↓
Position monitor
  ↓
Automatic outcome resolver
  ↓
Analytics / calibration / research

REAL MONEY EXECUTION:
DISABLED
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.dirname(
    BASE_DIR
)

if PROJECT_ROOT not in sys.path:

    sys.path.insert(
        0,
        PROJECT_ROOT,
    )


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env",
    ),
    override=True,
)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    ),
    override=True,
)

UPSTOX_ACCESS_TOKEN = os.getenv(
    "UPSTOX_ACCESS_TOKEN"
)

PAPER_TRADING_ENABLED = True

REAL_ORDER_EXECUTION = False


# ============================================================
# DATABASE
# ============================================================

try:

    from database.db import (
        initialize_database,
        insert_signal,
        insert_model_prediction,
        get_recent_signals,
        get_signal_count,
        get_prediction_count,
        database_path,
    )

    DATABASE_LOADED = True

except Exception as exc:

    DATABASE_LOADED = False

    DATABASE_IMPORT_ERROR = str(
        exc
    )

    print(
        "DATABASE IMPORT ERROR:",
        repr(exc),
    )

    def initialize_database():
        return None

    def insert_signal(**kwargs):
        return None

    def insert_model_prediction(**kwargs):
        return None

    def get_recent_signals(
        limit: int = 50,
    ):
        return []

    def get_signal_count():
        return 0

    def get_prediction_count():
        return 0

    def database_path():

        return os.path.join(
            PROJECT_ROOT,
            "database",
            "trading.db",
        )


# ============================================================
# ML ENGINE
# ============================================================

try:

    from ml import (
        FEATURES,
        predict,
        model_status,
    )

    ML_ENGINE_LOADED = True

except Exception as exc:

    ML_ENGINE_LOADED = False

    ML_IMPORT_ERROR = str(
        exc
    )

    print(
        "ML ENGINE IMPORT ERROR:",
        repr(exc),
    )

    FEATURES = []

    def predict(candles):

        raise RuntimeError(
            ML_IMPORT_ERROR
        )

    def model_status():

        return {
            "status":
                "error",
            "model_loaded":
                False,
            "error":
                ML_IMPORT_ERROR,
        }


# ============================================================
# DECISION ENGINE
# ============================================================

try:

    from ai.decision_engine import (
        evaluate_trade,
    )

    DECISION_ENGINE_LOADED = True

except Exception as exc:

    DECISION_ENGINE_LOADED = False

    print(
        "DECISION ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def evaluate_trade(
        analysis,
        symbol=None,
        portfolio=None,
    ):

        return {
            "decision":
                "NO_TRADE",

            "quality_score":
                0,

            "model_signal":
                analysis.get(
                    "signal",
                    "WAIT",
                ),

            "final_signal":
                analysis.get(
                    "signal",
                    "WAIT",
                ),

            "directional_probability":
                0,

            "directional_edge":
                0,

            "reasons":
                [],

            "blockers":
                [
                    "Decision engine unavailable."
                ],

            "score_breakdown":
                {},

            "risk_reward":
                0,
        }


# ============================================================
# RISK ENGINE
# ============================================================

try:

    from trading.risk import (
        RiskConfig,
        calculate_risk,
    )

    RISK_ENGINE_LOADED = True

except Exception as exc:

    RISK_ENGINE_LOADED = False

    print(
        "RISK ENGINE IMPORT ERROR:",
        repr(exc),
    )

    class RiskConfig:

        def __init__(
            self,
            risk_percent=1.0,
            **kwargs,
        ):

            self.risk_percent = (
                risk_percent
            )

    def calculate_risk(**kwargs):

        return {
            "risk_decision":
                "REJECT",

            "risk_score":
                0,

            "quantity":
                0,

            "maximum_loss":
                0,

            "risk_per_share":
                0,

            "trade_value":
                0,

            "reasons":
                [],

            "warnings":
                [],

            "blockers":
                [
                    "Risk engine unavailable."
                ],
        }


# ============================================================
# PAPER ENGINE
# ============================================================

try:

    from trading.paper import (
        execute_paper_trade,
        close_paper_trade_db,
        get_open_database_trades,
        get_database_trade,
    )

    PAPER_ENGINE_LOADED = True

except Exception as exc:

    PAPER_ENGINE_LOADED = False

    print(
        "PAPER ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def execute_paper_trade(
        **kwargs
    ):

        raise RuntimeError(
            "Paper execution engine unavailable."
        )

    def close_paper_trade_db(
        **kwargs
    ):

        raise RuntimeError(
            "Paper execution engine unavailable."
        )

    def get_open_database_trades():

        return []

    def get_database_trade(
        trade_id
    ):

        return None


# ============================================================
# POSITION MONITOR
# ============================================================

try:

    from trading.monitor import (
        create_monitor,
    )

    MONITOR_ENGINE_LOADED = True

except Exception as exc:

    MONITOR_ENGINE_LOADED = False

    print(
        "MONITOR ENGINE IMPORT ERROR:",
        repr(exc),
    )

    create_monitor = None


# ============================================================
# ANALYTICS ENGINE
# ============================================================

try:

    from trading.analytics import (
        generate_performance_report,
        generate_summary,
    )

    ANALYTICS_ENGINE_LOADED = True

except Exception as exc:

    ANALYTICS_ENGINE_LOADED = False

    ANALYTICS_ENGINE_IMPORT_ERROR = str(
        exc
    )

    print(
        "ANALYTICS ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def generate_performance_report(
        starting_capital=100000.0,
    ):

        return {
            "status":
                "error",
            "error":
                ANALYTICS_ENGINE_IMPORT_ERROR,
        }

    def generate_summary(
        starting_capital=100000.0,
    ):

        return {
            "status":
                "error",
            "error":
                ANALYTICS_ENGINE_IMPORT_ERROR,
        }


# ============================================================
# OUTCOME ENGINE
# ============================================================

try:

    from ai.outcome import (
        initialize_outcome_tables,
        create_prediction_outcome,
        resolve_prediction_outcome,
        outcome_summary,
        get_open_outcomes,
    )

    OUTCOME_ENGINE_LOADED = True

except Exception as exc:

    OUTCOME_ENGINE_LOADED = False

    OUTCOME_ENGINE_IMPORT_ERROR = str(
        exc
    )

    print(
        "OUTCOME ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def initialize_outcome_tables():
        return None

    def create_prediction_outcome(
        **kwargs
    ):

        return None

    def resolve_prediction_outcome(
        *args,
        **kwargs,
    ):

        raise RuntimeError(
            OUTCOME_ENGINE_IMPORT_ERROR
        )

    def outcome_summary():

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

    def get_open_outcomes():

        return []


# ============================================================
# CALIBRATION ENGINE
# ============================================================

try:

    from ai.calibration import (
        calibrate_probability,
        build_calibration_table,
    )

    CALIBRATION_ENGINE_LOADED = True

except Exception as exc:

    CALIBRATION_ENGINE_LOADED = False

    CALIBRATION_ENGINE_IMPORT_ERROR = str(
        exc
    )

    print(
        "CALIBRATION ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def calibrate_probability(
        signal,
        raw_probability,
    ):

        return {
            "raw_probability":
                raw_probability,
            "calibrated_probability":
                raw_probability,
            "method":
                "IDENTITY",
            "band":
                "UNKNOWN",
            "observations":
                0,
            "reliable":
                False,
        }

    def build_calibration_table():

        return {}


# ============================================================
# MODEL REGISTRY
# ============================================================

try:

    from ai.model_registry import (
        production_model,
        register_candidate,
        promote_candidate,
    )

    MODEL_REGISTRY_LOADED = True

except Exception as exc:

    MODEL_REGISTRY_LOADED = False

    print(
        "MODEL REGISTRY IMPORT ERROR:",
        repr(exc),
    )

    def production_model():

        return {
            "model":
                "V15",
            "version":
                "V15",
        }

    def register_candidate(
        name,
        version,
        validation,
    ):

        return {
            "name":
                name,
            "version":
                version,
            "validation":
                validation,
        }

    def promote_candidate(
        name,
        version,
        validation_gate,
    ):

        raise RuntimeError(
            "Model registry unavailable."
        )


# ============================================================
# V16 ENGINE
# ============================================================

try:

    from trading.v16_engine import (
        calibrate_model_output,
        create_outcome_record,
        v16_summary,
    )

    V16_ENGINE_LOADED = True

except Exception as exc:

    V16_ENGINE_LOADED = False

    print(
        "V16 ENGINE IMPORT ERROR:",
        repr(exc),
    )

    def calibrate_model_output(
        analysis
    ):

        return analysis

    def create_outcome_record(
        analysis,
        signal_id=None,
        trade_id=None,
    ):

        return None

    def v16_summary():

        return {
            "production_model":
                production_model(),
            "outcome_summary":
                outcome_summary(),
        }


# ============================================================
# AUTOMATIC OUTCOME RESOLVER
# ============================================================

try:

    from trading.outcome_resolver import (
        initialize_resolver_table,
        resolve_pending,
        resolver_status,
    )

    OUTCOME_RESOLVER_LOADED = True

except Exception as exc:

    OUTCOME_RESOLVER_LOADED = False

    OUTCOME_RESOLVER_IMPORT_ERROR = str(
        exc
    )

    print(
        "OUTCOME RESOLVER IMPORT ERROR:",
        repr(exc),
    )

    def initialize_resolver_table():
        return None

    def resolver_status():

        return {
            "status":
                "error",
            "resolver_loaded":
                False,
            "error":
                OUTCOME_RESOLVER_IMPORT_ERROR,
        }

    def resolve_pending(
        get_price,
        max_items=50,
    ):

        return {
            "status":
                "error",
            "resolver_loaded":
                False,
            "error":
                OUTCOME_RESOLVER_IMPORT_ERROR,
        }


# ============================================================
# PREDICTION INTEGRITY GATE
# ============================================================

try:

    from trading.prediction_gate import (
        initialize_prediction_gate,
        claim_prediction_slot,
        attach_prediction,
        gate_status,
    )

    PREDICTION_GATE_LOADED = True

except Exception as exc:

    PREDICTION_GATE_LOADED = False

    PREDICTION_GATE_IMPORT_ERROR = str(
        exc
    )

    print(
        "PREDICTION GATE IMPORT ERROR:",
        repr(exc),
    )

    def initialize_prediction_gate():
        return None

    def claim_prediction_slot(
        symbol,
        model_version,
        interval_minutes=5,
        candle_timestamp=None,
    ):

        return {
            "allowed":
                True,
            "reason":
                "GATE_UNAVAILABLE",
        }

    def attach_prediction(
        gate_id,
        prediction_id=None,
        signal_id=None,
    ):

        return None

    def gate_status():

        return {
            "status":
                "error",
            "gate_loaded":
                False,
            "error":
                PREDICTION_GATE_IMPORT_ERROR,
        }


# ============================================================
# GLOBAL STATE
# ============================================================

POSITION_MONITOR = None

MONITOR_TASK = None

MONITOR_INTERVAL_SECONDS = 5


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="India AI Trader V16",
    version="16.0.0",
    description=(
        "Integrated AI trading research, "
        "paper execution, risk management, "
        "prediction integrity, outcomes and analytics."
    ),
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# UPSTOX
# ============================================================

UPSTOX_V3 = (
    "https://api.upstox.com/v3"
)

NIFTY_TOKEN = (
    "NSE_INDEX|Nifty 50"
)

BANKNIFTY_TOKEN = (
    "NSE_INDEX|Nifty Bank"
)

VIX_TOKEN = (
    "NSE_INDEX|India VIX"
)


# ============================================================
# STOCK UNIVERSE
# ============================================================

STOCKS = {

    "RELIANCE":
        "NSE_EQ|INE002A01018",

    "TCS":
        "NSE_EQ|INE467B01029",

    "INFY":
        "NSE_EQ|INE009A01021",

    "HDFCBANK":
        "NSE_EQ|INE040A01034",

    "ICICIBANK":
        "NSE_EQ|INE090A01021",

    "SBIN":
        "NSE_EQ|INE062A01020",

    "ITC":
        "NSE_EQ|INE154A01025",

    "BHARTIARTL":
        "NSE_EQ|INE397D01024",

    "LT":
        "NSE_EQ|INE018A01030",

    "AXISBANK":
        "NSE_EQ|INE238A01034",
}


# ============================================================
# LOCAL DATA
# ============================================================

DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
)

os.makedirs(
    DATA_DIR,
    exist_ok=True,
)

WATCHLIST_FILE = os.path.join(
    DATA_DIR,
    "watchlist.json",
)

PORTFOLIO_FILE = os.path.join(
    DATA_DIR,
    "portfolio.json",
)

PAPER_TRADES_FILE = os.path.join(
    DATA_DIR,
    "paper_trades.json",
)


# ============================================================
# HELPERS
# ============================================================

def now_iso():

    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_float(
    value,
    default=0.0,
):

    try:

        if value is None:

            return default

        result = float(
            value
        )

        if not math.isfinite(
            result
        ):

            return default

        return result

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_int(
    value,
    default=0,
):

    try:

        return int(value)

    except Exception:

        return default


def clean_json(
    value,
):

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key):
                clean_json(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        list,
    ):

        return [
            clean_json(item)
            for item in value
        ]

    if isinstance(
        value,
        tuple,
    ):

        return [
            clean_json(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            np.integer,
            np.int64,
            np.int32,
        ),
    ):

        return int(value)

    if isinstance(
        value,
        (
            np.floating,
            np.float32,
            np.float64,
        ),
    ):

        result = float(
            value
        )

        if math.isfinite(
            result
        ):

            return result

        return None

    if isinstance(
        value,
        float,
    ):

        if math.isfinite(
            value
        ):

            return value

        return None

    if isinstance(
        value,
        pd.Timestamp,
    ):

        return value.isoformat()

    return value


def load_json(
    path,
    default,
):

    try:

        if not os.path.exists(
            path
        ):

            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    except Exception as exc:

        print(
            "JSON LOAD ERROR:",
            path,
            repr(exc),
        )

        return default


def save_json(
    path,
    data,
):

    temporary = (
        path + ".tmp"
    )

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
        )

    os.replace(
        temporary,
        path,
    )


def attach_candle_timestamp(
    analysis,
    candles,
):

    result = dict(
        analysis
    )

    result[
        "candle_timestamp"
    ] = None

    try:

        if (
            candles is not None
            and
            len(candles) > 0
            and
            "timestamp" in candles.columns
        ):

            result[
                "candle_timestamp"
            ] = str(
                candles.iloc[-1][
                    "timestamp"
                ]
            )

    except Exception:

        result[
            "candle_timestamp"
        ] = None

    return result


# ============================================================
# STATE
# ============================================================

WATCHLIST = load_json(
    WATCHLIST_FILE,
    [
        "RELIANCE",
        "TCS",
        "INFY",
        "HDFCBANK",
        "SBIN",
    ],
)

PORTFOLIO = load_json(
    PORTFOLIO_FILE,
    {
        "starting_capital":
            100000.0,
        "cash":
            100000.0,
        "positions":
            [],
        "created_at":
            now_iso(),
    },
)

PAPER_TRADES = load_json(
    PAPER_TRADES_FILE,
    [],
)


# ============================================================
# CACHE
# ============================================================

QUOTE_CACHE = {}

CANDLE_CACHE = {}

QUOTE_CACHE_SECONDS = 3

CANDLE_CACHE_SECONDS = 10


# ============================================================
# UPSTOX
# ============================================================

def require_token():

    global UPSTOX_ACCESS_TOKEN

    if not UPSTOX_ACCESS_TOKEN:

        load_dotenv(
            os.path.join(
                BASE_DIR,
                ".env",
            ),
            override=True,
        )

        load_dotenv(
            os.path.join(
                PROJECT_ROOT,
                ".env",
            ),
            override=True,
        )

        UPSTOX_ACCESS_TOKEN = os.getenv(
            "UPSTOX_ACCESS_TOKEN"
        )

    if not UPSTOX_ACCESS_TOKEN:

        raise HTTPException(
            status_code=500,
            detail=(
                "UPSTOX_ACCESS_TOKEN "
                "is not configured."
            ),
        )

    return UPSTOX_ACCESS_TOKEN


def upstox_headers():

    return {
        "Accept":
            "application/json",
        "Authorization":
            (
                "Bearer "
                + require_token()
            ),
    }


def upstox_get(
    url,
    timeout=30,
):

    try:

        response = requests.get(
            url,
            headers=upstox_headers(),
            timeout=timeout,
        )

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "Unable to connect to Upstox.",
                "error":
                    str(exc),
            },
        )

    if response.status_code != 200:

        try:

            body = response.json()

        except Exception:

            body = response.text

        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message":
                    "Upstox API request failed.",
                "upstox":
                    body,
            },
        )

    try:

        return response.json()

    except Exception:

        raise HTTPException(
            status_code=502,
            detail=(
                "Invalid JSON returned by Upstox."
            ),
        )


# ============================================================
# QUOTES
# ============================================================

def get_quotes(
    instrument_keys,
):

    keys = list(
        dict.fromkeys(
            instrument_keys
        )
    )

    key_string = ",".join(
        keys
    )

    cached = QUOTE_CACHE.get(
        key_string
    )

    if cached:

        cached_at, payload = cached

        age = (
            datetime.now(
                timezone.utc
            )
            -
            cached_at
        ).total_seconds()

        if age < QUOTE_CACHE_SECONDS:

            return payload

    encoded = quote(
        key_string,
        safe=",",
    )

    url = (
        f"{UPSTOX_V3}"
        f"/market-quote/ltp"
        f"?instrument_key={encoded}"
    )

    payload = upstox_get(
        url
    )

    QUOTE_CACHE[
        key_string
    ] = (
        datetime.now(
            timezone.utc
        ),
        payload,
    )

    return payload


def normalize_quote(
    raw,
    symbol,
):

    if not raw:

        return {
            "symbol":
                symbol,
            "last_price":
                None,
            "previous_close":
                None,
            "change":
                None,
            "change_percent":
                None,
            "volume":
                None,
            "ltq":
                None,
            "instrument_token":
                None,
            "timestamp":
                now_iso(),
        }

    last_price = safe_float(
        raw.get(
            "last_price"
        )
    )

    previous_close = safe_float(
        raw.get(
            "cp"
        )
    )

    if previous_close == 0:

        previous_close = safe_float(
            raw.get(
                "ohlc",
                {},
            ).get(
                "close"
            )
        )

    change = (
        last_price -
        previous_close
        if previous_close
        else 0.0
    )

    change_percent = (
        change /
        previous_close *
        100
        if previous_close
        else 0.0
    )

    return {
        "symbol":
            symbol,
        "last_price":
            round(
                last_price,
                2,
            ),
        "previous_close":
            round(
                previous_close,
                2,
            ),
        "change":
            round(
                change,
                2,
            ),
        "change_percent":
            round(
                change_percent,
                2,
            ),
        "volume":
            raw.get(
                "volume"
            ),
        "ltq":
            raw.get(
                "ltq"
            ),
        "instrument_token":
            raw.get(
                "instrument_token"
            ),
        "timestamp":
            now_iso(),
    }


def resolve_stock(
    symbol,
):

    clean_symbol = (
        str(symbol)
        .strip()
        .upper()
    )

    if clean_symbol in STOCKS:

        return STOCKS[
            clean_symbol
        ]

    if "|" in clean_symbol:

        return clean_symbol

    raise HTTPException(
        status_code=404,
        detail=(
            f"Unsupported stock: "
            f"{symbol}"
        ),
    )


def get_single_quote(
    symbol,
    instrument_key=None,
):

    clean_symbol = (
        str(symbol)
        .strip()
        .upper()
    )

    if instrument_key is None:

        instrument_key = resolve_stock(
            clean_symbol
        )

    payload = get_quotes(
        [
            instrument_key
        ]
    )

    data = payload.get(
        "data",
        {},
    )

    raw = data.get(
        instrument_key
    )

    if raw is None and data:

        raw = next(
            iter(
                data.values()
            ),
            None,
        )

    return normalize_quote(
        raw,
        clean_symbol,
    )


# ============================================================
# CANDLES
# ============================================================

def fetch_candles(
    instrument_key,
    interval=5,
    days=30,
):

    interval = safe_int(
        interval,
        5,
    )

    allowed = {
        1,
        2,
        3,
        5,
        10,
        15,
        30,
        60,
    }

    if interval not in allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported interval. "
                "Use "
                "1,2,3,5,10,15,30,60."
            ),
        )

    days = max(
        1,
        min(
            safe_int(
                days,
                30,
            ),
            30,
        ),
    )

    cache_key = (
        f"{instrument_key}:"
        f"{interval}:"
        f"{days}"
    )

    cached = CANDLE_CACHE.get(
        cache_key
    )

    if cached:

        cached_at, dataframe = cached

        age = (
            datetime.now(
                timezone.utc
            )
            -
            cached_at
        ).total_seconds()

        if age < CANDLE_CACHE_SECONDS:

            return dataframe.copy()

    encoded_key = quote(
        instrument_key,
        safe="",
    )

    to_date = datetime.now().date()

    from_date = (
        to_date -
        timedelta(
            days=days
        )
    )

    url = (
        f"{UPSTOX_V3}"
        f"/historical-candle/"
        f"{encoded_key}/"
        f"minutes/"
        f"{interval}/"
        f"{to_date}/"
        f"{from_date}"
    )

    payload = upstox_get(
        url
    )

    raw_candles = (
        payload
        .get(
            "data",
            {},
        )
        .get(
            "candles",
            [],
        )
    )

    rows = []

    for candle in raw_candles:

        if len(candle) < 6:

            continue

        rows.append({
            "timestamp":
                candle[0],

            "open":
                safe_float(
                    candle[1]
                ),

            "high":
                safe_float(
                    candle[2]
                ),

            "low":
                safe_float(
                    candle[3]
                ),

            "close":
                safe_float(
                    candle[4]
                ),

            "volume":
                safe_float(
                    candle[5]
                ),

            "open_interest":
                (
                    safe_float(
                        candle[6]
                    )
                    if len(candle) > 6
                    else 0
                ),
        })

    if not rows:

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "No historical candle data.",
                "instrument_key":
                    instrument_key,
            },
        )

    dataframe = (
        pd.DataFrame(rows)
        .drop_duplicates(
            subset=[
                "timestamp"
            ]
        )
        .sort_values(
            "timestamp"
        )
        .reset_index(
            drop=True
        )
    )

    CANDLE_CACHE[
        cache_key
    ] = (
        datetime.now(
            timezone.utc
        ),
        dataframe.copy(),
    )

    return dataframe


# ============================================================
# V15 MODEL
# ============================================================

def run_v15(
    candles,
):

    if not ML_ENGINE_LOADED:

        raise RuntimeError(
            "V15 ML engine is not loaded."
        )

    if len(candles) < 220:

        close = (
            safe_float(
                candles.iloc[-1][
                    "close"
                ]
            )
            if len(candles)
            else 0.0
        )

        return {
            "signal":
                "WAIT",

            "raw_model_signal":
                "WAIT",

            "confidence":
                0.0,

            "score":
                0.0,

            "reason":
                (
                    f"Only {len(candles)} "
                    "candles available."
                ),

            "engine":
                "V15_XGBOOST_ML",

            "model_loaded":
                True,

            "model_version":
                "V15",

            "feature_count":
                len(FEATURES),

            "probabilities":
                {
                    "BUY":
                        0.0,
                    "WAIT":
                        100.0,
                    "SELL":
                        0.0,
                },

            "entry":
                close,

            "stop_loss":
                None,

            "target_1":
                None,

            "target_2":
                None,

            "risk_reward":
                None,

            "market_regime":
                "UNKNOWN",
        }

    result = predict(
        candles
    )

    if isinstance(
        result,
        list,
    ):

        result = result[
            0
        ]

    if not isinstance(
        result,
        dict,
    ):

        result = {
            "signal":
                str(result)
        }

    result[
        "model_version"
    ] = result.get(
        "model_version",
        "V15",
    )

    result[
        "feature_count"
    ] = len(FEATURES)

    return result


# ============================================================
# CALIBRATION
# ============================================================

def apply_calibration(
    analysis,
):

    if CALIBRATION_ENGINE_LOADED:

        try:

            result = (
                calibrate_model_output(
                    analysis
                )
            )

            if isinstance(
                result,
                dict,
            ):

                return result

        except Exception as exc:

            print(
                "CALIBRATION ERROR:",
                repr(exc),
            )

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

    calibrated = {}

    for direction in (
        "BUY",
        "SELL",
        "WAIT",
    ):

        raw = safe_float(
            probabilities.get(
                direction
            )
        )

        try:

            result = (
                calibrate_probability(
                    direction,
                    raw,
                )
            )

            calibrated[
                direction
            ] = safe_float(
                result.get(
                    "calibrated_probability",
                    raw,
                )
            )

        except Exception:

            calibrated[
                direction
            ] = raw

    analysis[
        "calibrated_probabilities"
    ] = calibrated

    analysis[
        "production_model"
    ] = production_model()

    return analysis


# ============================================================
# DECISION
# ============================================================

def build_decision(
    symbol,
    analysis,
):

    return evaluate_trade(
        analysis=
            analysis,

        symbol=
            symbol,

        portfolio=
            PORTFOLIO,
    )


# ============================================================
# RISK
# ============================================================

def build_risk(
    symbol,
    analysis,
):

    signal = str(
        analysis.get(
            "signal",
            "WAIT",
        )
    ).upper()

    if signal not in {
        "BUY",
        "SELL",
    }:

        return {
            "risk_decision":
                "REJECT",

            "risk_score":
                0,

            "symbol":
                symbol,

            "side":
                signal,

            "quantity":
                0,

            "maximum_loss":
                0,

            "risk_per_share":
                0,

            "trade_value":
                0,

            "reasons":
                [
                    "No directional signal."
                ],

            "warnings":
                [],

            "blockers":
                [
                    "V15 produced WAIT."
                ],
        }

    return calculate_risk(
        symbol=
            symbol,

        side=
            signal,

        entry=
            analysis.get(
                "entry"
            ),

        stop_loss=
            analysis.get(
                "stop_loss"
            ),

        target_1=
            analysis.get(
                "target_1"
            ),

        target_2=
            analysis.get(
                "target_2"
            ),

        risk_reward=
            analysis.get(
                "risk_reward"
            ),

        portfolio=
            PORTFOLIO,

        paper_trades=
            PAPER_TRADES,

        config=
            RiskConfig(),
    )


# ============================================================
# PERSISTENCE + PREDICTION GATE
# ============================================================

def persist_prediction(
    symbol,
    analysis,
):

    if not DATABASE_LOADED:

        return {
            "saved":
                False,

            "reason":
                "Database unavailable.",
        }

    try:

        model_version = (
            analysis.get(
                "model_version",
                "V15",
            )
        )

        candle_timestamp = (
            analysis.get(
                "candle_timestamp"
            )
        )

        # ----------------------------------------------------
        # PREDICTION INTEGRITY GATE
        # ----------------------------------------------------

        gate = claim_prediction_slot(
            symbol=
                symbol,

            model_version=
                model_version,

            interval_minutes=
                5,

            candle_timestamp=
                candle_timestamp,
        )

        if not gate.get(
            "allowed",
            True,
        ):

            return {
                "saved":
                    False,

                "duplicate":
                    True,

                "reason":
                    gate.get(
                        "reason",
                        "DUPLICATE_CANDLE",
                    ),

                "existing_prediction_id":
                    gate.get(
                        "prediction_id"
                    ),

                "existing_signal_id":
                    gate.get(
                        "signal_id"
                    ),

                "gate_id":
                    gate.get(
                        "gate_id"
                    ),

                "candle_timestamp":
                    candle_timestamp,
            }

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

        signal = str(
            analysis.get(
                "signal",
                "WAIT",
            )
        ).upper()

        decision = (
            analysis.get(
                "decision",
                {},
            )
            or {}
        )

        decision_name = (
            decision.get(
                "decision"
            )
            if isinstance(
                decision,
                dict,
            )
            else None
        )

        if not decision_name:

            decision_name = (
                "PAPER_CANDIDATE"
                if signal in {
                    "BUY",
                    "SELL",
                }
                else "NO_TRADE"
            )

        reason_json = json.dumps(
            {
                "model_reason":
                    analysis.get(
                        "reason"
                    ),

                "decision":
                    decision,

                "risk":
                    analysis.get(
                        "risk"
                    ),

                "calibrated_probabilities":
                    analysis.get(
                        "calibrated_probabilities"
                    ),
            }
        )

        signal_id = insert_signal(
            symbol=
                symbol,

            timestamp=
                analysis.get(
                    "timestamp",
                    now_iso(),
                ),

            model_version=
                model_version,

            signal=
                signal,

            buy_probability=
                safe_float(
                    probabilities.get(
                        "BUY"
                    )
                ),

            sell_probability=
                safe_float(
                    probabilities.get(
                        "SELL"
                    )
                ),

            wait_probability=
                safe_float(
                    probabilities.get(
                        "WAIT"
                    )
                ),

            market_regime=
                analysis.get(
                    "market_regime"
                ),

            entry=
                analysis.get(
                    "entry"
                ),

            stop_loss=
                analysis.get(
                    "stop_loss"
                ),

            target_1=
                analysis.get(
                    "target_1"
                ),

            target_2=
                analysis.get(
                    "target_2"
                ),

            risk_reward=
                analysis.get(
                    "risk_reward"
                ),

            decision=
                decision_name,

            decision_reason=
                reason_json,

            created_at=
                now_iso(),
        )

        prediction_id = (
            insert_model_prediction(
                signal_id=
                    signal_id,

                symbol=
                    symbol,

                model_version=
                    model_version,

                prediction=
                    signal,

                buy_probability=
                    safe_float(
                        probabilities.get(
                            "BUY"
                        )
                    ),

                sell_probability=
                    safe_float(
                        probabilities.get(
                            "SELL"
                        )
                    ),

                wait_probability=
                    safe_float(
                        probabilities.get(
                            "WAIT"
                        )
                    ),

                features_hash=
                    None,

                created_at=
                    now_iso(),
            )
        )

        # ----------------------------------------------------
        # Attach database IDs to prediction gate.
        # ----------------------------------------------------

        attach_prediction(
            gate_id=
                gate.get(
                    "gate_id"
                ),

            prediction_id=
                prediction_id,

            signal_id=
                signal_id,
        )

        return {
            "saved":
                True,

            "duplicate":
                False,

            "signal_id":
                signal_id,

            "prediction_id":
                prediction_id,

            "gate_id":
                gate.get(
                    "gate_id"
                ),

            "candle_timestamp":
                candle_timestamp,
        }

    except Exception as exc:

        print(
            "PERSISTENCE ERROR:",
            repr(exc),
        )

        return {
            "saved":
                False,

            "error":
                str(exc),
        }


# ============================================================
# OUTCOME CREATION
# ============================================================

def create_outcome_for_prediction(
    analysis,
    persistence,
):

    if not OUTCOME_ENGINE_LOADED:

        return None

    if not persistence.get(
        "saved"
    ):

        return None

    try:

        return create_outcome_record(
            analysis,

            signal_id=
                persistence.get(
                    "signal_id"
                ),
        )

    except Exception as exc:

        print(
            "OUTCOME CREATE ERROR:",
            repr(exc),
        )

        return None


# ============================================================
# PRICE
# ============================================================

def get_position_price(
    symbol,
):

    instrument = resolve_stock(
        symbol
    )

    quote_data = get_single_quote(
        symbol,
        instrument,
    )

    price = quote_data.get(
        "last_price"
    )

    if price is None:

        raise RuntimeError(
            f"Price unavailable for {symbol}"
        )

    return safe_float(
        price
    )


# ============================================================
# PAPER CLOSE
# ============================================================

def close_monitored_trade(
    trade_id,
    exit_price,
    exit_reason,
):

    result = close_paper_trade_db(
        trade_id=
            trade_id,

        exit_price=
            exit_price,

        exit_reason=
            exit_reason,

        portfolio=
            PORTFOLIO,
    )

    save_json(
        PORTFOLIO_FILE,
        PORTFOLIO,
    )

    return result


# ============================================================
# POSITION MONITOR INITIALIZATION
# ============================================================

def initialize_position_monitor():

    global POSITION_MONITOR

    if not MONITOR_ENGINE_LOADED:

        POSITION_MONITOR = None

        return

    if POSITION_MONITOR is not None:

        return

    POSITION_MONITOR = create_monitor(
        get_open_trades=
            get_open_database_trades,

        get_price=
            get_position_price,

        close_trade=
            close_monitored_trade,
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return clean_json({
        "status":
            "online",

        "application":
            "India AI Trader",

        "version":
            "16.0.0",

        "upstox_configured":
            bool(
                UPSTOX_ACCESS_TOKEN
            ),

        "ml_engine_loaded":
            ML_ENGINE_LOADED,

        "decision_engine_loaded":
            DECISION_ENGINE_LOADED,

        "risk_engine_loaded":
            RISK_ENGINE_LOADED,

        "paper_engine_loaded":
            PAPER_ENGINE_LOADED,

        "monitor_engine_loaded":
            MONITOR_ENGINE_LOADED,

        "analytics_engine_loaded":
            ANALYTICS_ENGINE_LOADED,

        "outcome_engine_loaded":
            OUTCOME_ENGINE_LOADED,

        "calibration_engine_loaded":
            CALIBRATION_ENGINE_LOADED,

        "model_registry_loaded":
            MODEL_REGISTRY_LOADED,

        "v16_engine_loaded":
            V16_ENGINE_LOADED,

        "outcome_resolver_loaded":
            OUTCOME_RESOLVER_LOADED,

        "prediction_gate_loaded":
            PREDICTION_GATE_LOADED,

        "database_loaded":
            DATABASE_LOADED,

        "feature_count":
            len(FEATURES),

        "production_model":
            production_model(),

        "paper_trading":
            True,

        "real_money":
            False,

        "timestamp":
            now_iso(),
    })


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/api/health"
)
def health():

    return clean_json({
        "status":
            "healthy",

        "version":
            "16.0.0",

        "upstox_configured":
            bool(
                UPSTOX_ACCESS_TOKEN
            ),

        "ml_engine_loaded":
            ML_ENGINE_LOADED,

        "decision_engine_loaded":
            DECISION_ENGINE_LOADED,

        "risk_engine_loaded":
            RISK_ENGINE_LOADED,

        "paper_engine_loaded":
            PAPER_ENGINE_LOADED,

        "monitor_engine_loaded":
            MONITOR_ENGINE_LOADED,

        "analytics_engine_loaded":
            ANALYTICS_ENGINE_LOADED,

        "outcome_engine_loaded":
            OUTCOME_ENGINE_LOADED,

        "calibration_engine_loaded":
            CALIBRATION_ENGINE_LOADED,

        "model_registry_loaded":
            MODEL_REGISTRY_LOADED,

        "v16_engine_loaded":
            V16_ENGINE_LOADED,

        "outcome_resolver_loaded":
            OUTCOME_RESOLVER_LOADED,

        "prediction_gate_loaded":
            PREDICTION_GATE_LOADED,

        "monitor_running":
            POSITION_MONITOR is not None,

        "database_loaded":
            DATABASE_LOADED,

        "feature_count":
            len(FEATURES),

        "paper_trading":
            True,

        "real_order_execution":
            False,

        "production_model":
            production_model(),

        "timestamp":
            now_iso(),
    })


# ============================================================
# MODEL STATUS
# ============================================================

@app.get(
    "/api/model/status"
)
def model_status_api():

    try:

        status = model_status()

        if not isinstance(
            status,
            dict,
        ):

            status = {}

        model_path = status.get(
            "model_path",
            os.path.join(
                BASE_DIR,
                "ml_model.joblib",
            ),
        )

        return clean_json({
            "status":
                status.get(
                    "status",
                    "success",
                ),

            "model_loaded":
                bool(
                    status.get(
                        "model_loaded",
                        False,
                    )
                ),

            "model_exists":
                bool(
                    status.get(
                        "model_exists",
                        os.path.exists(
                            model_path
                        ),
                    )
                ),

            "model_path":
                model_path,

            "model_type":
                status.get(
                    "model_type"
                ),

            "feature_count":
                len(FEATURES),

            "features":
                FEATURES,

            "version":
                status.get(
                    "version",
                    "V15",
                ),

            "classes":
                status.get(
                    "classes",
                    {
                        "0":
                            "SELL",
                        "1":
                            "WAIT",
                        "2":
                            "BUY",
                    },
                ),

            "error":
                status.get(
                    "error"
                ),

            "backend_version":
                "16.0.0",

            "production_model":
                production_model(),

            "decision_engine_loaded":
                DECISION_ENGINE_LOADED,

            "risk_engine_loaded":
                RISK_ENGINE_LOADED,

            "paper_engine_loaded":
                PAPER_ENGINE_LOADED,

            "monitor_engine_loaded":
                MONITOR_ENGINE_LOADED,

            "analytics_engine_loaded":
                ANALYTICS_ENGINE_LOADED,

            "outcome_engine_loaded":
                OUTCOME_ENGINE_LOADED,

            "calibration_engine_loaded":
                CALIBRATION_ENGINE_LOADED,

            "model_registry_loaded":
                MODEL_REGISTRY_LOADED,

            "v16_engine_loaded":
                V16_ENGINE_LOADED,

            "outcome_resolver_loaded":
                OUTCOME_RESOLVER_LOADED,

            "prediction_gate_loaded":
                PREDICTION_GATE_LOADED,

            "database_loaded":
                DATABASE_LOADED,

            "database_path":
                database_path(),

            "paper_trading":
                True,

            "real_order_execution":
                False,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        return {
            "status":
                "error",

            "model_loaded":
                False,

            "model_exists":
                os.path.exists(
                    os.path.join(
                        BASE_DIR,
                        "ml_model.joblib",
                    )
                ),

            "model_path":
                os.path.join(
                    BASE_DIR,
                    "ml_model.joblib",
                ),

            "feature_count":
                len(FEATURES),

            "features":
                FEATURES,

            "version":
                "V15",

            "production_model":
                production_model(),

            "error":
                str(exc),

            "timestamp":
                now_iso(),
        }


# ============================================================
# DATABASE STATUS
# ============================================================

@app.get(
    "/api/database/status"
)
def database_status():

    try:

        initialize_database()

        return clean_json({
            "status":
                "success",

            "database":
                "SQLite",

            "connected":
                True,

            "path":
                database_path(),

            "signal_count":
                get_signal_count(),

            "prediction_count":
                get_prediction_count(),

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        return {
            "status":
                "error",

            "database":
                "SQLite",

            "connected":
                False,

            "path":
                database_path(),

            "error":
                str(exc),

            "timestamp":
                now_iso(),
        }


# ============================================================
# MARKET INDICES
# ============================================================

@app.get(
    "/api/market/indices"
)
def market_indices():

    payload = get_quotes(
        [
            NIFTY_TOKEN,
            BANKNIFTY_TOKEN,
            VIX_TOKEN,
        ]
    )

    data = payload.get(
        "data",
        {},
    )

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "data":
            data,

        "processed":
            {
                "nifty":
                    normalize_quote(
                        data.get(
                            "NSE_INDEX:Nifty 50"
                        ),
                        "NIFTY 50",
                    ),

                "banknifty":
                    normalize_quote(
                        data.get(
                            "NSE_INDEX:Nifty Bank"
                        ),
                        "BANK NIFTY",
                    ),

                "vix":
                    normalize_quote(
                        data.get(
                            "NSE_INDEX:India VIX"
                        ),
                        "INDIA VIX",
                    ),
            },

        "timestamp":
            now_iso(),
    })


# ============================================================
# SINGLE STOCK AI
# ============================================================

@app.get(
    "/api/ai/stock/{symbol}"
)
@app.get(
    "/api/ai/signal/{symbol}"
)
def stock_ai(
    symbol: str,
):

    clean_symbol = (
        symbol
        .strip()
        .upper()
    )

    instrument = resolve_stock(
        clean_symbol
    )

    quote_data = get_single_quote(
        clean_symbol,
        instrument,
    )

    candles = fetch_candles(
        instrument,
        5,
        30,
    )

    analysis = run_v15(
        candles
    )

    analysis = apply_calibration(
        analysis
    )

    analysis = attach_candle_timestamp(
        analysis,
        candles,
    )

    analysis[
        "symbol"
    ] = clean_symbol

    analysis[
        "timestamp"
    ] = now_iso()

    decision = build_decision(
        clean_symbol,
        analysis,
    )

    analysis[
        "decision"
    ] = decision

    risk = build_risk(
        clean_symbol,
        analysis,
    )

    analysis[
        "risk"
    ] = risk

    persistence = persist_prediction(
        clean_symbol,
        analysis,
    )

    outcome_id = (
        create_outcome_for_prediction(
            analysis,
            persistence,
        )
    )

    analysis[
        "outcome_id"
    ] = outcome_id

    allowed = (
        decision.get(
            "decision"
        )
        ==
        "TRADE"
        and
        risk.get(
            "risk_decision"
        )
        in {
            "APPROVE",
            "REDUCE",
        }
    )

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "stock":
            clean_symbol,

        "production_model":
            production_model(),

        "quote":
            quote_data,

        "model":
            analysis,

        "decision":
            decision,

        "risk":
            risk,

        "final_action":
            (
                "PAPER_TRADE_CANDIDATE"
                if allowed
                else
                "NO_TRADE"
            ),

        "persistence":
            persistence,

        "outcome_id":
            outcome_id,

        "timestamp":
            now_iso(),
    })


# ============================================================
# MARKET AI SIGNAL
# ============================================================

@app.get(
    "/api/ai/signal"
)
def ai_signal():

    try:

        nifty_candles = fetch_candles(
            NIFTY_TOKEN,
            5,
            30,
        )

        bank_candles = fetch_candles(
            BANKNIFTY_TOKEN,
            5,
            30,
        )

        nifty = run_v15(
            nifty_candles
        )

        bank = run_v15(
            bank_candles
        )

        nifty = apply_calibration(
            nifty
        )

        bank = apply_calibration(
            bank
        )

        nifty = attach_candle_timestamp(
            nifty,
            nifty_candles,
        )

        bank = attach_candle_timestamp(
            bank,
            bank_candles,
        )

        nifty[
            "symbol"
        ] = "NIFTY 50"

        bank[
            "symbol"
        ] = "BANK NIFTY"

        nifty[
            "timestamp"
        ] = now_iso()

        bank[
            "timestamp"
        ] = now_iso()

        nifty[
            "decision"
        ] = build_decision(
            "NIFTY 50",
            nifty,
        )

        bank[
            "decision"
        ] = build_decision(
            "BANK NIFTY",
            bank,
        )

        nifty[
            "risk"
        ] = build_risk(
            "NIFTY 50",
            nifty,
        )

        bank[
            "risk"
        ] = build_risk(
            "BANK NIFTY",
            bank,
        )

        nifty_persistence = (
            persist_prediction(
                "NIFTY 50",
                nifty,
            )
        )

        bank_persistence = (
            persist_prediction(
                "BANK NIFTY",
                bank,
            )
        )

        nifty_outcome = (
            create_outcome_for_prediction(
                nifty,
                nifty_persistence,
            )
        )

        bank_outcome = (
            create_outcome_for_prediction(
                bank,
                bank_persistence,
            )
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "V16 AI signal failed.",
                "error":
                    str(exc),
            },
        )

    nifty_probs = (
        nifty.get(
            "probabilities",
            {},
        )
        or {}
    )

    bank_probs = (
        bank.get(
            "probabilities",
            {},
        )
        or {}
    )

    buy = (
        safe_float(
            nifty_probs.get(
                "BUY"
            )
        )
        * 0.55
        +
        safe_float(
            bank_probs.get(
                "BUY"
            )
        )
        * 0.45
    )

    sell = (
        safe_float(
            nifty_probs.get(
                "SELL"
            )
        )
        * 0.55
        +
        safe_float(
            bank_probs.get(
                "SELL"
            )
        )
        * 0.45
    )

    wait = (
        safe_float(
            nifty_probs.get(
                "WAIT"
            )
        )
        * 0.55
        +
        safe_float(
            bank_probs.get(
                "WAIT"
            )
        )
        * 0.45
    )

    if (
        buy >= 55
        and
        buy > sell + 10
        and
        buy > wait
    ):

        final_signal = "BUY"

    elif (
        sell >= 55
        and
        sell > buy + 10
        and
        sell > wait
    ):

        final_signal = "SELL"

    else:

        final_signal = "WAIT"

    regime_map = {
        "STRONG BULLISH":
            5,

        "BULLISH":
            4,

        "SIDEWAYS":
            3,

        "BEARISH":
            2,

        "STRONG BEARISH":
            1,
    }

    regime_score = (
        regime_map.get(
            nifty.get(
                "market_regime",
                "SIDEWAYS",
            ),
            3,
        )
        +
        regime_map.get(
            bank.get(
                "market_regime",
                "SIDEWAYS",
            ),
            3,
        )
    )

    if regime_score >= 9:

        market_regime = (
            "STRONG BULLISH"
        )

    elif regime_score >= 7:

        market_regime = "BULLISH"

    elif regime_score <= 3:

        market_regime = (
            "STRONG BEARISH"
        )

    elif regime_score <= 5:

        market_regime = "BEARISH"

    else:

        market_regime = "SIDEWAYS"

    market_analysis = {
        "signal":
            final_signal,

        "raw_model_signal":
            final_signal,

        "probabilities":
            {
                "BUY":
                    round(
                        buy,
                        2,
                    ),

                "SELL":
                    round(
                        sell,
                        2,
                    ),

                "WAIT":
                    round(
                        wait,
                        2,
                    ),
            },

        "market_regime":
            market_regime,

        "entry":
            None,

        "risk_reward":
            None,
    }

    market_decision = evaluate_trade(
        analysis=
            market_analysis,

        symbol=
            "MARKET",

        portfolio=
            PORTFOLIO,
    )

    vix = get_single_quote(
        "INDIA VIX",
        VIX_TOKEN,
    )

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "ai_signal":
            final_signal,

        "confidence":
            round(
                max(
                    buy,
                    sell,
                    wait,
                ),
                2,
            ),

        "score":
            round(
                buy -
                sell,
                2,
            ),

        "market_regime":
            market_regime,

        "engine":
            "V16_INTEGRATED_INTELLIGENCE",

        "production_model":
            production_model(),

        "model_loaded":
            ML_ENGINE_LOADED,

        "decision_engine_loaded":
            DECISION_ENGINE_LOADED,

        "risk_engine_loaded":
            RISK_ENGINE_LOADED,

        "paper_engine_loaded":
            PAPER_ENGINE_LOADED,

        "monitor_engine_loaded":
            MONITOR_ENGINE_LOADED,

        "analytics_engine_loaded":
            ANALYTICS_ENGINE_LOADED,

        "outcome_engine_loaded":
            OUTCOME_ENGINE_LOADED,

        "calibration_engine_loaded":
            CALIBRATION_ENGINE_LOADED,

        "outcome_resolver_loaded":
            OUTCOME_RESOLVER_LOADED,

        "prediction_gate_loaded":
            PREDICTION_GATE_LOADED,

        "v16_engine_loaded":
            V16_ENGINE_LOADED,

        "combined_probabilities":
            {
                "BUY":
                    round(
                        buy,
                        2,
                    ),

                "SELL":
                    round(
                        sell,
                        2,
                    ),

                "WAIT":
                    round(
                        wait,
                        2,
                    ),
            },

        "nifty_signal":
            nifty,

        "banknifty_signal":
            bank,

        "market_decision":
            market_decision,

        "vix":
            vix,

        "persistence":
            {
                "nifty":
                    nifty_persistence,

                "banknifty":
                    bank_persistence,
            },

        "outcomes":
            {
                "nifty":
                    nifty_outcome,

                "banknifty":
                    bank_outcome,
            },

        "paper_trading":
            {
                "enabled":
                    True,

                "real_orders":
                    False,

                "status":
                    "PAPER_ONLY",
            },

        "timestamp":
            now_iso(),
    })


# ============================================================
# TRADE EVALUATION
# ============================================================

@app.get(
    "/api/trade/evaluate/{symbol}"
)
def trade_evaluation(
    symbol: str,
):

    clean_symbol = (
        symbol
        .strip()
        .upper()
    )

    instrument = resolve_stock(
        clean_symbol
    )

    candles = fetch_candles(
        instrument,
        5,
        30,
    )

    analysis = run_v15(
        candles
    )

    analysis = apply_calibration(
        analysis
    )

    analysis = attach_candle_timestamp(
        analysis,
        candles,
    )

    analysis[
        "symbol"
    ] = clean_symbol

    analysis[
        "timestamp"
    ] = now_iso()

    decision = build_decision(
        clean_symbol,
        analysis,
    )

    risk = build_risk(
        clean_symbol,
        analysis,
    )

    analysis[
        "decision"
    ] = decision

    analysis[
        "risk"
    ] = risk

    allowed = (
        decision.get(
            "decision"
        )
        ==
        "TRADE"
        and
        risk.get(
            "risk_decision"
        )
        in {
            "APPROVE",
            "REDUCE",
        }
    )

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "symbol":
            clean_symbol,

        "production_model":
            production_model(),

        "model":
            analysis,

        "decision":
            decision,

        "risk":
            risk,

        "final_action":
            (
                "PAPER_TRADE_CANDIDATE"
                if allowed
                else
                "NO_TRADE"
            ),

        "timestamp":
            now_iso(),
    })


# ============================================================
# DECISION
# ============================================================

@app.get(
    "/api/decision/{symbol}"
)
def decision_api(
    symbol: str,
):

    return trade_evaluation(
        symbol
    )


# ============================================================
# PAPER EXECUTION
# ============================================================

class ExecutePaperTradeRequest(
    BaseModel
):

    side: Optional[str] = None

    signal_id: Optional[int] = None

    entry_price: Optional[float] = None

    stop_loss: Optional[float] = None

    target_price: Optional[float] = None

    risk_percent: float = Field(
        default=1.0,
        gt=0,
        le=2.0,
    )


@app.post(
    "/api/paper/execute/{symbol}"
)
def execute_ai_paper_trade(
    symbol: str,
    payload: ExecutePaperTradeRequest,
):

    if not PAPER_TRADING_ENABLED:

        raise HTTPException(
            status_code=403,
            detail=(
                "Paper trading is disabled."
            ),
        )

    clean_symbol = (
        symbol
        .strip()
        .upper()
    )

    instrument = resolve_stock(
        clean_symbol
    )

    quote_data = get_single_quote(
        clean_symbol,
        instrument,
    )

    live_price = safe_float(
        quote_data.get(
            "last_price"
        )
    )

    candles = fetch_candles(
        instrument,
        5,
        30,
    )

    analysis = run_v15(
        candles
    )

    analysis = apply_calibration(
        analysis
    )

    analysis = attach_candle_timestamp(
        analysis,
        candles,
    )

    analysis[
        "symbol"
    ] = clean_symbol

    analysis[
        "timestamp"
    ] = now_iso()

    analysis[
        "entry"
    ] = (
        payload.entry_price
        if payload.entry_price is not None
        else live_price
    )

    if payload.stop_loss is not None:

        analysis[
            "stop_loss"
        ] = payload.stop_loss

    if payload.target_price is not None:

        analysis[
            "target_1"
        ] = payload.target_price

    model_signal = str(
        analysis.get(
            "signal",
            "WAIT",
        )
    ).upper()

    requested_side = (
        payload.side.upper()
        if payload.side
        else model_signal
    )

    if requested_side not in {
        "BUY",
        "SELL",
    }:

        return clean_json({
            "status":
                "rejected",

            "stage":
                "MODEL",

            "model_signal":
                model_signal,

            "real_order_sent":
                False,
        })

    if requested_side != model_signal:

        return clean_json({
            "status":
                "rejected",

            "stage":
                "SAFETY",

            "message":
                (
                    "Requested side does not "
                    "match current V15 signal."
                ),

            "requested_side":
                requested_side,

            "model_signal":
                model_signal,

            "real_order_sent":
                False,
        })

    decision = build_decision(
        clean_symbol,
        analysis,
    )

    analysis[
        "decision"
    ] = decision

    if decision.get(
        "decision"
    ) != "TRADE":

        return clean_json({
            "status":
                "rejected",

            "stage":
                "DECISION",

            "symbol":
                clean_symbol,

            "model":
                analysis,

            "decision":
                decision,

            "message":
                "Decision engine rejected the trade.",

            "real_order_sent":
                False,
        })

    risk = calculate_risk(
        symbol=
            clean_symbol,

        side=
            requested_side,

        entry=
            analysis.get(
                "entry"
            ),

        stop_loss=
            analysis.get(
                "stop_loss"
            ),

        target_1=
            analysis.get(
                "target_1"
            ),

        target_2=
            analysis.get(
                "target_2"
            ),

        risk_reward=
            analysis.get(
                "risk_reward"
            ),

        portfolio=
            PORTFOLIO,

        paper_trades=
            PAPER_TRADES,

        config=
            RiskConfig(
                risk_percent=
                    payload.risk_percent
            ),
    )

    analysis[
        "risk"
    ] = risk

    if risk.get(
        "risk_decision"
    ) not in {
        "APPROVE",
        "REDUCE",
    }:

        return clean_json({
            "status":
                "rejected",

            "stage":
                "RISK",

            "symbol":
                clean_symbol,

            "model":
                analysis,

            "decision":
                decision,

            "risk":
                risk,

            "message":
                "Risk engine rejected the trade.",

            "real_order_sent":
                False,
        })

    quantity = safe_int(
        risk.get(
            "quantity"
        )
    )

    if quantity <= 0:

        return clean_json({
            "status":
                "rejected",

            "stage":
                "RISK",

            "risk":
                risk,

            "message":
                "Risk engine calculated zero quantity.",

            "real_order_sent":
                False,
        })

    execution = execute_paper_trade(
        symbol=
            clean_symbol,

        side=
            requested_side,

        quantity=
            quantity,

        entry_price=
            safe_float(
                analysis.get(
                    "entry"
                ),
                live_price,
            ),

        stop_loss=
            analysis.get(
                "stop_loss"
            ),

        target_price=
            analysis.get(
                "target_1"
            ),

        signal_id=
            payload.signal_id,

        portfolio=
            PORTFOLIO,
    )

    save_json(
        PORTFOLIO_FILE,
        PORTFOLIO,
    )

    outcome_id = None

    if OUTCOME_ENGINE_LOADED:

        try:

            outcome_id = (
                create_outcome_record(
                    analysis,

                    signal_id=
                        payload.signal_id,

                    trade_id=
                        execution.get(
                            "trade_id"
                        )
                    if isinstance(
                        execution,
                        dict,
                    )
                    else None,
                )
            )

        except Exception as exc:

            print(
                "EXECUTION OUTCOME ERROR:",
                repr(exc),
            )

    return clean_json({
        "status":
            "success",

        "execution_mode":
            "PAPER",

        "real_order_sent":
            False,

        "model":
            analysis,

        "decision":
            decision,

        "risk":
            risk,

        "execution":
            execution,

        "outcome_id":
            outcome_id,

        "timestamp":
            now_iso(),
    })


# ============================================================
# PAPER DATABASE TRADES
# ============================================================

@app.get(
    "/api/paper/db/trades"
)
def database_paper_trades():

    try:

        trades = (
            get_open_database_trades()
        )

        return clean_json({
            "status":
                "success",

            "source":
                "SQLite",

            "count":
                len(trades),

            "trades":
                trades,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Unable to load paper trades.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# CLOSE PAPER TRADE
# ============================================================

class ClosePaperTradeRequest(
    BaseModel
):

    exit_price: Optional[
        float
    ] = None

    exit_reason: str = (
        "MANUAL"
    )


@app.post(
    "/api/paper/db/trades/{trade_id}/close"
)
def close_database_paper_trade(
    trade_id: int,
    payload: ClosePaperTradeRequest,
):

    trade = get_database_trade(
        trade_id
    )

    if trade is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Database paper trade "
                "not found."
            ),
        )

    exit_price = (
        payload.exit_price
    )

    if exit_price is None:

        exit_price = get_position_price(
            trade[
                "symbol"
            ]
        )

    result = close_monitored_trade(
        trade_id,
        exit_price,
        payload.exit_reason,
    )

    return clean_json({
        "status":
            "success",

        "execution_mode":
            "PAPER",

        "execution":
            result,

        "real_order_sent":
            False,

        "timestamp":
            now_iso(),
    })


# ============================================================
# POSITION MONITOR
# ============================================================

@app.get(
    "/api/paper/monitor"
)
def monitor_paper_positions():

    initialize_position_monitor()

    if POSITION_MONITOR is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Position monitor "
                "is not initialized."
            ),
        )

    try:

        return clean_json(
            POSITION_MONITOR.scan()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Paper position monitoring failed.",
                "error":
                    str(exc),
            },
        )


@app.get(
    "/api/paper/monitor/status"
)
def monitor_status():

    initialize_position_monitor()

    if POSITION_MONITOR is None:

        return {
            "status":
                "error",

            "monitor_loaded":
                False,

            "timestamp":
                now_iso(),
        }

    return clean_json({
        "status":
            "success",

        "monitor_loaded":
            True,

        "last_scan_at":
            POSITION_MONITOR.last_scan_at,

        "last_result":
            POSITION_MONITOR.last_result,

        "monitor_interval_seconds":
            MONITOR_INTERVAL_SECONDS,

        "execution_mode":
            "PAPER",

        "real_money":
            False,

        "timestamp":
            now_iso(),
    })


# ============================================================
# ANALYTICS
# ============================================================

@app.get(
    "/api/analytics/summary"
)
def analytics_summary():

    if not ANALYTICS_ENGINE_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Analytics engine "
                "is unavailable."
            ),
        )

    try:

        starting_capital = safe_float(
            PORTFOLIO.get(
                "starting_capital",
                100000.0,
            ),
            100000.0,
        )

        return clean_json(
            generate_summary(
                starting_capital
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Analytics summary failed.",
                "error":
                    str(exc),
            },
        )


@app.get(
    "/api/analytics/performance"
)
def analytics_performance():

    if not ANALYTICS_ENGINE_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Analytics engine "
                "is unavailable."
            ),
        )

    try:

        starting_capital = safe_float(
            PORTFOLIO.get(
                "starting_capital",
                100000.0,
            ),
            100000.0,
        )

        return clean_json(
            generate_performance_report(
                starting_capital
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Performance analytics failed.",
                "error":
                    str(exc),
            },
        )


@app.get(
    "/api/analytics/metrics"
)
def analytics_metrics():

    if not ANALYTICS_ENGINE_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Analytics engine "
                "is unavailable."
            ),
        )

    try:

        report = (
            generate_performance_report(
                safe_float(
                    PORTFOLIO.get(
                        "starting_capital",
                        100000.0,
                    ),
                    100000.0,
                )
            )
        )

        summary = report.get(
            "summary",
            {},
        )

        equity = report.get(
            "equity",
            {},
        )

        return clean_json({
            "status":
                "success",

            "trade_count":
                summary.get(
                    "trade_count",
                    0,
                ),

            "win_rate":
                summary.get(
                    "win_rate",
                    0,
                ),

            "profit_factor":
                summary.get(
                    "profit_factor",
                    0,
                ),

            "net_pnl":
                summary.get(
                    "net_pnl",
                    0,
                ),

            "expectancy_per_trade":
                summary.get(
                    "expectancy_per_trade",
                    0,
                ),

            "max_drawdown":
                equity.get(
                    "max_drawdown",
                    0,
                ),

            "max_drawdown_percent":
                equity.get(
                    "max_drawdown_percent",
                    0,
                ),

            "return_percent":
                equity.get(
                    "total_return_percent",
                    0,
                ),

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Analytics metrics failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# V16 STATUS
# ============================================================

@app.get(
    "/api/v16/status"
)
def v16_status():

    try:

        summary = v16_summary()

    except Exception as exc:

        summary = {
            "error":
                str(exc),
        }

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "production_model":
            production_model(),

        "outcomes":
            outcome_summary(),

        "outcome_resolver":
            (
                resolver_status()
                if OUTCOME_RESOLVER_LOADED
                else
                {
                    "status":
                        "unavailable",
                }
            ),

        "prediction_gate":
            (
                gate_status()
                if PREDICTION_GATE_LOADED
                else
                {
                    "status":
                        "unavailable",
                }
            ),

        "engines":
            {
                "ml":
                    ML_ENGINE_LOADED,

                "decision":
                    DECISION_ENGINE_LOADED,

                "risk":
                    RISK_ENGINE_LOADED,

                "paper":
                    PAPER_ENGINE_LOADED,

                "monitor":
                    MONITOR_ENGINE_LOADED,

                "analytics":
                    ANALYTICS_ENGINE_LOADED,

                "outcome":
                    OUTCOME_ENGINE_LOADED,

                "calibration":
                    CALIBRATION_ENGINE_LOADED,

                "registry":
                    MODEL_REGISTRY_LOADED,

                "v16":
                    V16_ENGINE_LOADED,

                "outcome_resolver":
                    OUTCOME_RESOLVER_LOADED,

                "prediction_gate":
                    PREDICTION_GATE_LOADED,
            },

        "summary":
            summary,

        "paper_only":
            True,

        "real_money":
            False,

        "timestamp":
            now_iso(),
    })


# ============================================================
# V16 OUTCOMES
# ============================================================

@app.get(
    "/api/v16/outcomes"
)
def v16_outcomes():

    return clean_json({
        "status":
            "success",

        "summary":
            outcome_summary(),

        "open_outcomes":
            get_open_outcomes(),

        "resolver":
            (
                resolver_status()
                if OUTCOME_RESOLVER_LOADED
                else None
            ),

        "timestamp":
            now_iso(),
    })


# ============================================================
# PREDICTION GATE STATUS
# ============================================================

@app.get(
    "/api/v16/prediction-gate/status"
)
def prediction_gate_status():

    if not PREDICTION_GATE_LOADED:

        return {
            "status":
                "error",

            "gate_loaded":
                False,

            "timestamp":
                now_iso(),
        }

    try:

        status = gate_status()

        return clean_json({
            "status":
                "success",

            "gate_loaded":
                True,

            **status,

            "interval_minutes":
                5,

            "paper_only":
                True,

            "real_money":
                False,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Prediction gate status failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# OUTCOME RESOLVER STATUS
# ============================================================

@app.get(
    "/api/v16/outcome-resolver/status"
)
def outcome_resolver_status():

    if not OUTCOME_RESOLVER_LOADED:

        return {
            "status":
                "error",

            "resolver_loaded":
                False,

            "timestamp":
                now_iso(),
        }

    try:

        status = resolver_status()

        return clean_json({
            "status":
                "success",

            "resolver_loaded":
                True,

            **status,

            "interval_seconds":
                MONITOR_INTERVAL_SECONDS,

            "paper_only":
                True,

            "real_money":
                False,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Outcome resolver status failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# V16 CALIBRATION
# ============================================================

@app.get(
    "/api/v16/calibration"
)
def v16_calibration():

    if not CALIBRATION_ENGINE_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Calibration engine "
                "is unavailable."
            ),
        )

    try:

        return clean_json({
            "status":
                "success",

            "calibration":
                build_calibration_table(),

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Calibration failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# OUTCOME RESOLUTION API
# ============================================================

class OutcomeResolutionRequest(
    BaseModel
):

    price_5m: Optional[
        float
    ] = None

    price_15m: Optional[
        float
    ] = None

    price_30m: Optional[
        float
    ] = None

    price_60m: Optional[
        float
    ] = None

    max_favorable_price: Optional[
        float
    ] = None

    max_adverse_price: Optional[
        float
    ] = None


@app.post(
    "/api/v16/outcomes/{outcome_id}/resolve"
)
def resolve_v16_outcome(
    outcome_id: int,
    payload: OutcomeResolutionRequest,
):

    if not OUTCOME_ENGINE_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Outcome engine "
                "is unavailable."
            ),
        )

    try:

        result = (
            resolve_prediction_outcome(
                outcome_id,

                price_5m=
                    payload.price_5m,

                price_15m=
                    payload.price_15m,

                price_30m=
                    payload.price_30m,

                price_60m=
                    payload.price_60m,

                max_favorable_price=
                    payload.max_favorable_price,

                max_adverse_price=
                    payload.max_adverse_price,
            )
        )

        return clean_json({
            "status":
                "success",

            "outcome":
                result,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Outcome resolution failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# MODEL REGISTRY
# ============================================================

@app.get(
    "/api/v16/model"
)
def v16_model():

    return clean_json({
        "status":
            "success",

        "production_model":
            production_model(),

        "registry_loaded":
            MODEL_REGISTRY_LOADED,

        "timestamp":
            now_iso(),
    })


class ModelCandidateRequest(
    BaseModel
):

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    version: str = Field(
        min_length=1,
        max_length=50,
    )

    validation: Dict[str, Any]


@app.post(
    "/api/v16/model/register"
)
def register_v16_model(
    payload: ModelCandidateRequest,
):

    if not MODEL_REGISTRY_LOADED:

        raise HTTPException(
            status_code=500,
            detail=(
                "Model registry unavailable."
            ),
        )

    try:

        result = register_candidate(
            name=
                payload.name,

            version=
                payload.version,

            validation=
                payload.validation,
        )

        return clean_json({
            "status":
                "success",

            "candidate":
                result,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Candidate registration failed.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# WATCHLIST
# ============================================================

class WatchlistRequest(
    BaseModel
):

    symbol: str


@app.get(
    "/api/watchlist"
)
def get_watchlist():

    results = []

    for symbol in WATCHLIST:

        try:

            instrument = resolve_stock(
                symbol
            )

            quote_data = get_single_quote(
                symbol,
                instrument,
            )

            results.append({
                "symbol":
                    symbol,

                "quote":
                    quote_data,
            })

        except Exception as exc:

            results.append({
                "symbol":
                    symbol,

                "error":
                    str(exc),
            })

    return clean_json({
        "status":
            "success",

        "watchlist":
            results,

        "count":
            len(WATCHLIST),

        "timestamp":
            now_iso(),
    })


@app.post(
    "/api/watchlist"
)
def add_watchlist(
    payload: WatchlistRequest,
):

    symbol = (
        payload.symbol
        .strip()
        .upper()
    )

    resolve_stock(
        symbol
    )

    if symbol not in WATCHLIST:

        WATCHLIST.append(
            symbol
        )

        save_json(
            WATCHLIST_FILE,
            WATCHLIST,
        )

    return {
        "status":
            "success",

        "symbol":
            symbol,

        "watchlist":
            WATCHLIST,
    }


@app.delete(
    "/api/watchlist/{symbol}"
)
def remove_watchlist(
    symbol: str,
):

    symbol = (
        symbol
        .strip()
        .upper()
    )

    if symbol in WATCHLIST:

        WATCHLIST.remove(
            symbol
        )

        save_json(
            WATCHLIST_FILE,
            WATCHLIST,
        )

    return {
        "status":
            "success",

        "watchlist":
            WATCHLIST,
    }


# ============================================================
# SCANNER
# ============================================================

@app.get(
    "/api/scanner"
)
def scanner(
    limit: int = Query(
        10,
        ge=1,
        le=25,
    ),
):

    results = []

    for symbol, instrument in STOCKS.items():

        try:

            quote_data = get_single_quote(
                symbol,
                instrument,
            )

            candles = fetch_candles(
                instrument,
                5,
                30,
            )

            if len(candles) < 220:

                continue

            analysis = run_v15(
                candles
            )

            analysis = apply_calibration(
                analysis
            )

            probabilities = (
                analysis.get(
                    "probabilities",
                    {},
                )
                or {}
            )

            buy = safe_float(
                probabilities.get(
                    "BUY"
                )
            )

            sell = safe_float(
                probabilities.get(
                    "SELL"
                )
            )

            wait = safe_float(
                probabilities.get(
                    "WAIT"
                )
            )

            signal = str(
                analysis.get(
                    "signal",
                    "WAIT",
                )
            ).upper()

            decision = build_decision(
                symbol,
                analysis,
            )

            risk = build_risk(
                symbol,
                analysis,
            )

            results.append({
                "symbol":
                    symbol,

                "price":
                    quote_data.get(
                        "last_price"
                    ),

                "change_percent":
                    quote_data.get(
                        "change_percent"
                    ),

                "signal":
                    signal,

                "confidence":
                    max(
                        buy,
                        sell,
                        wait,
                    ),

                "buy_probability":
                    buy,

                "sell_probability":
                    sell,

                "wait_probability":
                    wait,

                "calibrated_probabilities":
                    analysis.get(
                        "calibrated_probabilities"
                    ),

                "market_regime":
                    analysis.get(
                        "market_regime",
                        "UNKNOWN",
                    ),

                "entry":
                    analysis.get(
                        "entry"
                    ),

                "stop_loss":
                    analysis.get(
                        "stop_loss"
                    ),

                "target_1":
                    analysis.get(
                        "target_1"
                    ),

                "target_2":
                    analysis.get(
                        "target_2"
                    ),

                "risk_reward":
                    safe_float(
                        analysis.get(
                            "risk_reward"
                        )
                    ),

                "decision":
                    decision.get(
                        "decision",
                        "NO_TRADE",
                    ),

                "quality_score":
                    decision.get(
                        "quality_score",
                        0,
                    ),

                "risk_decision":
                    risk.get(
                        "risk_decision",
                        "REJECT",
                    ),

                "risk_score":
                    risk.get(
                        "risk_score",
                        0,
                    ),

                "quantity":
                    risk.get(
                        "quantity",
                        0,
                    ),

                "maximum_loss":
                    risk.get(
                        "maximum_loss",
                        0,
                    ),

                "decision_reasons":
                    decision.get(
                        "reasons",
                        [],
                    ),

                "decision_blockers":
                    decision.get(
                        "blockers",
                        [],
                    ),

                "risk_blockers":
                    risk.get(
                        "blockers",
                        [],
                    ),
            })

        except Exception as exc:

            print(
                "SCANNER ERROR:",
                symbol,
                repr(exc),
            )

    results.sort(
        key=lambda row:
            (
                safe_float(
                    row.get(
                        "quality_score"
                    )
                ),

                safe_float(
                    row.get(
                        "confidence"
                    )
                ),
            ),

        reverse=True,
    )

    return clean_json({
        "status":
            "success",

        "version":
            "16.0.0",

        "count":
            len(results),

        "results":
            results[:limit],

        "timestamp":
            now_iso(),
    })


# ============================================================
# PORTFOLIO
# ============================================================

class PortfolioResetRequest(
    BaseModel
):

    starting_capital: float = Field(
        gt=0,
        le=100_000_000,
    )


@app.get(
    "/api/portfolio"
)
def portfolio():

    cash = safe_float(
        PORTFOLIO.get(
            "cash",
            0,
        )
    )

    invested = 0.0

    market_value = 0.0

    unrealized_pnl = 0.0

    positions = []

    for position in PORTFOLIO.get(
        "positions",
        [],
    ):

        current = dict(
            position
        )

        try:

            current_price = get_position_price(
                position[
                    "symbol"
                ]
            )

            entry = safe_float(
                position.get(
                    "average_price"
                )
            )

            quantity = safe_int(
                position.get(
                    "quantity"
                )
            )

            side = str(
                position.get(
                    "side",
                    "BUY",
                )
            ).upper()

            invested += (
                entry *
                quantity
            )

            market_value += (
                current_price *
                quantity
            )

            if side == "BUY":

                pnl = (
                    current_price -
                    entry
                ) * quantity

            else:

                pnl = (
                    entry -
                    current_price
                ) * quantity

            unrealized_pnl += pnl

            current[
                "current_price"
            ] = round(
                current_price,
                2,
            )

            current[
                "unrealized_pnl"
            ] = round(
                pnl,
                2,
            )

        except Exception as exc:

            current[
                "error"
            ] = str(exc)

        positions.append(
            current
        )

    equity = (
        cash +
        market_value
    )

    starting = safe_float(
        PORTFOLIO.get(
            "starting_capital",
            100000.0,
        ),
        100000.0,
    )

    total_return = (
        (
            equity -
            starting
        )
        /
        starting *
        100
        if starting
        else 0
    )

    return clean_json({
        "status":
            "success",

        "starting_capital":
            starting,

        "cash":
            cash,

        "invested":
            invested,

        "market_value":
            market_value,

        "equity":
            equity,

        "unrealized_pnl":
            unrealized_pnl,

        "total_return_percent":
            total_return,

        "position_count":
            len(positions),

        "positions":
            positions,

        "timestamp":
            now_iso(),
    })


@app.post(
    "/api/portfolio/reset"
)
def reset_portfolio(
    payload: PortfolioResetRequest,
):

    global PORTFOLIO

    PORTFOLIO = {
        "starting_capital":
            float(
                payload.starting_capital
            ),

        "cash":
            float(
                payload.starting_capital
            ),

        "positions":
            [],

        "created_at":
            now_iso(),
    }

    save_json(
        PORTFOLIO_FILE,
        PORTFOLIO,
    )

    return {
        "status":
            "success",

        "message":
            "Paper portfolio reset.",

        "starting_capital":
            payload.starting_capital,

        "timestamp":
            now_iso(),
    }


# ============================================================
# PAPER PERFORMANCE
# ============================================================

@app.get(
    "/api/paper/performance"
)
def paper_performance():

    closed = [
        trade
        for trade in PAPER_TRADES
        if trade.get(
            "status"
        )
        ==
        "CLOSED"
    ]

    pnl_values = [
        safe_float(
            trade.get(
                "realized_pnl"
            )
        )
        for trade in closed
    ]

    winners = [
        pnl
        for pnl in pnl_values
        if pnl > 0
    ]

    losers = [
        pnl
        for pnl in pnl_values
        if pnl < 0
    ]

    gross_profit = sum(
        winners
    )

    gross_loss = abs(
        sum(
            losers
        )
    )

    win_rate = (
        len(winners) /
        len(closed) *
        100
        if closed
        else 0
    )

    profit_factor = (
        gross_profit /
        gross_loss
        if gross_loss > 0
        else (
            float("inf")
            if gross_profit > 0
            else 0
        )
    )

    account = portfolio()

    equity = safe_float(
        account[
            "equity"
        ]
    )

    starting = safe_float(
        account[
            "starting_capital"
        ]
    )

    return_percent = (
        (
            equity -
            starting
        )
        /
        starting *
        100
        if starting
        else 0
    )

    return clean_json({
        "status":
            "success",

        "total_trades":
            len(closed),

        "winning_trades":
            len(winners),

        "losing_trades":
            len(losers),

        "win_rate":
            round(
                win_rate,
                2,
            ),

        "total_pnl":
            round(
                sum(
                    pnl_values
                ),
                2,
            ),

        "profit_factor":
            (
                round(
                    profit_factor,
                    3,
                )
                if math.isfinite(
                    profit_factor
                )
                else "inf"
            ),

        "starting_capital":
            starting,

        "equity":
            equity,

        "return_percent":
            round(
                return_percent,
                2,
            ),

        "timestamp":
            now_iso(),
    })


# ============================================================
# SIGNAL HISTORY
# ============================================================

@app.get(
    "/api/signals/history"
)
def signals_history(
    limit: int = Query(
        50,
        ge=1,
        le=500,
    ),
):

    try:

        signals = (
            get_recent_signals(
                limit
            )
        )

        return clean_json({
            "status":
                "success",

            "count":
                len(signals),

            "signals":
                signals,

            "timestamp":
                now_iso(),
        })

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "message":
                    "Unable to load signals.",
                "error":
                    str(exc),
            },
        )


# ============================================================
# DECISION HISTORY
# ============================================================

@app.get(
    "/api/decisions/history"
)
def decisions_history(
    limit: int = Query(
        50,
        ge=1,
        le=500,
    ),
):

    signals = (
        get_recent_signals(
            limit
        )
    )

    decisions = []

    for signal in signals:

        raw_reason = signal.get(
            "decision_reason"
        )

        details = raw_reason

        if isinstance(
            raw_reason,
            str,
        ):

            try:

                details = json.loads(
                    raw_reason
                )

            except Exception:

                pass

        decisions.append({
            "id":
                signal.get(
                    "id"
                ),

            "symbol":
                signal.get(
                    "symbol"
                ),

            "timestamp":
                signal.get(
                    "timestamp"
                ),

            "model_version":
                signal.get(
                    "model_version"
                ),

            "signal":
                signal.get(
                    "signal"
                ),

            "decision":
                signal.get(
                    "decision"
                ),

            "buy_probability":
                signal.get(
                    "buy_probability"
                ),

            "sell_probability":
                signal.get(
                    "sell_probability"
                ),

            "wait_probability":
                signal.get(
                    "wait_probability"
                ),

            "market_regime":
                signal.get(
                    "market_regime"
                ),

            "entry":
                signal.get(
                    "entry"
                ),

            "stop_loss":
                signal.get(
                    "stop_loss"
                ),

            "target_1":
                signal.get(
                    "target_1"
                ),

            "target_2":
                signal.get(
                    "target_2"
                ),

            "risk_reward":
                signal.get(
                    "risk_reward"
                ),

            "details":
                details,
        })

    return clean_json({
        "status":
            "success",

        "count":
            len(decisions),

        "decisions":
            decisions,

        "timestamp":
            now_iso(),
    })


# ============================================================
# STARTUP
# ============================================================

@app.on_event(
    "startup"
)
async def startup():

    global MONITOR_TASK

    try:

        initialize_database()

    except Exception as exc:

        print(
            "DATABASE STARTUP ERROR:",
            repr(exc),
        )

    try:

        initialize_outcome_tables()

    except Exception as exc:

        print(
            "OUTCOME TABLE STARTUP ERROR:",
            repr(exc),
        )

    try:

        initialize_resolver_table()

    except Exception as exc:

        print(
            "OUTCOME RESOLVER TABLE STARTUP ERROR:",
            repr(exc),
        )

    try:

        initialize_prediction_gate()

    except Exception as exc:

        print(
            "PREDICTION GATE TABLE STARTUP ERROR:",
            repr(exc),
        )

    initialize_position_monitor()

    print()
    print(
        "=" * 76
    )

    print(
        "INDIA AI TRADER V16"
    )

    print(
        "=" * 76
    )

    print(
        "UPSTOX:",
        (
            "CONNECTED"
            if UPSTOX_ACCESS_TOKEN
            else
            "NOT CONFIGURED"
        ),
    )

    print(
        "V15 ML:",
        (
            "LOADED"
            if ML_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "CALIBRATION:",
        (
            "LOADED"
            if CALIBRATION_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "DECISION ENGINE:",
        (
            "LOADED"
            if DECISION_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "RISK ENGINE:",
        (
            "LOADED"
            if RISK_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "PAPER ENGINE:",
        (
            "LOADED"
            if PAPER_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "POSITION MONITOR:",
        (
            "LOADED"
            if POSITION_MONITOR is not None
            else
            "ERROR"
        ),
    )

    print(
        "OUTCOME ENGINE:",
        (
            "LOADED"
            if OUTCOME_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "ANALYTICS ENGINE:",
        (
            "LOADED"
            if ANALYTICS_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "MODEL REGISTRY:",
        (
            "LOADED"
            if MODEL_REGISTRY_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "V16 ENGINE:",
        (
            "LOADED"
            if V16_ENGINE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "OUTCOME RESOLVER:",
        (
            "LOADED"
            if OUTCOME_RESOLVER_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "PREDICTION GATE:",
        (
            "LOADED"
            if PREDICTION_GATE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "DATABASE:",
        (
            "CONNECTED"
            if DATABASE_LOADED
            else
            "ERROR"
        ),
    )

    print(
        "FEATURE COUNT:",
        len(FEATURES),
    )

    print(
        "PRODUCTION MODEL:",
        production_model(),
    )

    print(
        "PAPER TRADING:",
        "ENABLED",
    )

    print(
        "REAL MONEY:",
        "DISABLED",
    )

    print(
        "MONITOR INTERVAL:",
        f"{MONITOR_INTERVAL_SECONDS}s",
    )

    print(
        "=" * 76
    )

    if (
        POSITION_MONITOR is not None
        or
        OUTCOME_RESOLVER_LOADED
    ):

        MONITOR_TASK = (
            asyncio.create_task(
                background_monitor_loop()
            )
        )


# ============================================================
# BACKGROUND LOOP
# ============================================================

async def background_monitor_loop():

    while True:

        try:

            # ------------------------------------------------
            # POSITION MONITOR
            # ------------------------------------------------

            if POSITION_MONITOR is not None:

                try:

                    result = (
                        POSITION_MONITOR.scan()
                    )

                    if (
                        isinstance(
                            result,
                            dict,
                        )
                        and
                        result.get(
                            "closed",
                            0,
                        ) > 0
                    ):

                        print(
                            "PAPER MONITOR:",
                            (
                                "closed "
                                f"{result['closed']} "
                                "trade(s)."
                            ),
                        )

                except Exception as exc:

                    print(
                        "POSITION MONITOR ERROR:",
                        repr(exc),
                    )

            # ------------------------------------------------
            # AUTOMATIC OUTCOME RESOLVER
            # ------------------------------------------------

            if OUTCOME_RESOLVER_LOADED:

                try:

                    outcome_result = (
                        resolve_pending(
                            get_price=
                                get_position_price,

                            max_items=
                                25,
                        )
                    )

                    if not isinstance(
                        outcome_result,
                        dict,
                    ):

                        outcome_result = {}

                    resolved = safe_int(
                        outcome_result.get(
                            "resolved",
                            0,
                        )
                    )

                    milestones = safe_int(
                        outcome_result.get(
                            "milestones_updated",
                            0,
                        )
                    )

                    if (
                        resolved > 0
                        or
                        milestones > 0
                    ):

                        print(
                            "OUTCOME RESOLVER:",
                            (
                                f"milestones={milestones}, "
                                f"resolved={resolved}"
                            ),
                        )

                except Exception as exc:

                    print(
                        "OUTCOME RESOLVER ERROR:",
                        repr(exc),
                    )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            print(
                "BACKGROUND LOOP ERROR:",
                repr(exc),
            )

        await asyncio.sleep(
            MONITOR_INTERVAL_SECONDS
        )


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event(
    "shutdown"
)
async def shutdown():

    global MONITOR_TASK

    if MONITOR_TASK is not None:

        MONITOR_TASK.cancel()

        try:

            await MONITOR_TASK

        except asyncio.CancelledError:

            pass

        MONITOR_TASK = None