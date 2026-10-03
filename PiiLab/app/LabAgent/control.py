import json
import os
from pathlib import Path
from typing import Any

import boto3


REGION = os.getenv("AWS_REGION", "us-east-1")

comprehend = boto3.client("comprehend", region_name=REGION)

BASE_DIR = Path(__file__).resolve().parent

with (BASE_DIR / "pii-mask.json").open(
    "r",
    encoding="utf-8",
) as f:
    MASK_CONFIG = json.load(f)

PARTNER_ALLOWED_FIELDS = {"claim_id", "product", "serial_number", "status"}


def for_partner(claim: dict[str, Any]) -> dict[str, Any]:
    payload = {
        field: claim[field]
        for field in PARTNER_ALLOWED_FIELDS
        if field in claim
    }

    return payload


def entities(text: str) -> list[dict[str, Any]]:
    response = comprehend.detect_pii_entities(Text=text, LanguageCode="en")
    return response.get("Entities", [])


def _mask(text: str, detected: list[dict[str, Any]]) -> str:
    masked = text

    for entity in sorted(
        detected,
        key=lambda item: item["BeginOffset"],
        reverse=True,
    ):
        start = entity["BeginOffset"]
        end = entity["EndOffset"]
        entity_type = entity["Type"]

        replacement = MASK_CONFIG["entities"].get(
            entity_type,
            MASK_CONFIG["default_mask"],
        )

        masked = (
            masked[:start]
            + replacement
            + masked[end:]
        )

    return masked


def for_storage(record: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}

    for key, value in record.items():
        if isinstance(value, str):
            sanitized[key] = _mask(
                value,
                entities(value),
            )
        else:
            sanitized[key] = value

    return sanitized
