"""Enterprise FHIR Client interaction example.

Demonstrates resilient communication with cloud FHIR servers
(Google Cloud Healthcare API, Azure Health Data Services, AWS HealthLake, or HAPI)
using standard library urllib with automatic backoff and pagination.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fhir_lite import FHIRClient, Patient, Bundle


def run_client_workflow(base_endpoint: str, access_token: str) -> None:
    """Execute search, read, conditional creation, and batch transactions."""
    client = FHIRClient(
        base_url=base_endpoint,
        auth=access_token,
        max_retries=3,
        backoff_factor=0.5,
    )

    print(f"Connecting to FHIR endpoint: {base_endpoint}")

    # 1. Paged search iterator (transparently follows 'next' links)
    print("\n--- 1. Iterating search results ---")
    for patient in client.iter_search(Patient, family="Johnson", max_pages=3):
        print(f"Found patient: {patient.id} - active: {patient.data.get('active')}")

    # 2. Build and execute an atomic batch transaction
    print("\n--- 2. Building atomic transaction ---")
    tx = Bundle.transaction()
    tx.add_create(Patient(
        id="tx-pat-01",
        active=True,
        gender="male",
        name=[{"use": "official", "family": "Johnson", "given": ["Robert"]}],
    ))

    # In production with live server:
    # tx_outcome = client.transaction(tx)
    # print(f"Transaction committed with {len(tx_outcome.entries)} entries.")


if __name__ == "__main__":
    run_client_workflow(
        base_endpoint="https://hapi.fhir.org/baseR4",
        access_token="Bearer mock-token-for-demonstration",
    )
