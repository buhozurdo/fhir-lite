"""Production serverless handler example using fhir-lite.

Illustrates zero-cold-start FHIR resource validation, path extraction,
and bidirectional serialization in cloud function environments.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fhir_lite import from_json, Patient, OperationOutcome


def handle_event(event: Mapping[str, Any], context: Any = None) -> dict[str, Any]:
    """Serverless entrypoint (AWS Lambda / Google Cloud Functions / Azure Functions)."""
    body = event.get("body")
    if not body:
        outcome = OperationOutcome.issue(
            severity="error",
            code="invalid",
            diagnostics="Request payload body cannot be empty.",
        )
        return {"statusCode": 400, "body": json.dumps(outcome.data)}

    try:
        # 1. Zero-dependency deserialization & polymorphic detection
        resource = from_json(body if isinstance(body, str) else json.dumps(body))

        # 2. Schema and business validation
        errors = resource.validate()
        if errors:
            outcome = OperationOutcome.issue(
                severity="error",
                code="structure",
                diagnostics="; ".join(errors),
            )
            return {"statusCode": 422, "body": json.dumps(outcome.data)}

        # 3. Safe property extraction
        summary = {
            "resourceType": resource.resource_type,
            "id": getattr(resource, "id", None),
            "status": "valid",
        }

        if isinstance(resource, Patient):
            summary["gender"] = resource.data.get("gender")
            summary["family_name"] = resource.get_path("name.0.family", default="UNKNOWN")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/fhir+json"},
            "body": json.dumps(summary),
        }

    except Exception as exc:
        outcome = OperationOutcome.issue(
            severity="fatal",
            code="exception",
            diagnostics=f"Internal processing failure: {exc}",
        )
        return {"statusCode": 500, "body": json.dumps(outcome.data)}


if __name__ == "__main__":
    # Local simulation
    test_event = {
        "body": json.dumps({
            "resourceType": "Patient",
            "id": "srv-pat-01",
            "active": True,
            "gender": "female",
            "name": [{"use": "official", "family": "Curie", "given": ["Marie"]}],
        })
    }
    response = handle_event(test_event)
    print("Serverless execution result:")
    print(response)
