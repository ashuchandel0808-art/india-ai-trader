"""
INDIA AI TRADER V16
MODEL REGISTRY

Never replace a working model blindly.

Models are candidates until validation promotes them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

REGISTRY_PATH = os.path.join(
    BASE_DIR,
    "model_registry.json",
)


def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_registry():

    if not os.path.exists(
        REGISTRY_PATH
    ):

        return {
            "production":
                {
                    "model":
                        "V15",
                    "version":
                        "V15",
                },
            "candidates":
                [],
            "history":
                [],
        }

    with open(
        REGISTRY_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_registry(
    registry,
):

    temporary = (
        REGISTRY_PATH +
        ".tmp"
    )

    with open(
        temporary,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            registry,
            file,
            indent=2,
        )

    os.replace(
        temporary,
        REGISTRY_PATH,
    )


def register_candidate(
    name: str,
    version: str,
    validation: Dict[str, Any],
):

    registry = load_registry()

    candidate = {
        "name":
            name,
        "version":
            version,
        "registered_at":
            now_iso(),
        "validation":
            validation,
    }

    registry[
        "candidates"
    ].append(
        candidate
    )

    save_registry(
        registry
    )

    return candidate


def promote_candidate(
    name: str,
    version: str,
    validation_gate: Dict[str, Any],
):

    if not validation_gate.get(
        "promote"
    ):

        raise ValueError(
            "Candidate failed promotion gate."
        )

    registry = load_registry()

    previous = registry.get(
        "production"
    )

    registry[
        "history"
    ].append({
        "event":
            "PROMOTE",
        "previous":
            previous,
        "timestamp":
            now_iso(),
    })

    registry[
        "production"
    ] = {
        "model":
            name,
        "version":
            version,
        "promoted_at":
            now_iso(),
    }

    save_registry(
        registry
    )

    return registry[
        "production"
    ]


def production_model():

    return load_registry().get(
        "production"
    )