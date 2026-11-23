"""High-throughput FHIR Bulk Data (NDJSON) streaming and de-identification ETL.

Demonstrates streaming multi-gigabyte clinical datasets line-by-line with
constant O(1) memory overhead and automated HIPAA Safe Harbor sanitization.
"""

from __future__ import annotations

import gzip
import io
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fhir_lite import (
    iter_ndjson_raw,
    anonymize,
    DeidConfig,
    evaluate_fhirpath,
)


def process_bulk_stream(stream_input: io.BufferedReader) -> int:
    """Stream and sanitize clinical resources on the fly."""
    deid_rules = DeidConfig(
        date_handling="year_only",
        pseudonymize_id=True,
        salt="enterprise-clinical-vault-key-2026",
        keep_state_and_country=True,
    )

    records_processed = 0

    # Lazy iteration over raw NDJSON payloads (zero intermediate allocation)
    for raw_resource in iter_ndjson_raw(stream_input):
        # 1. HIPAA Safe Harbor transformation
        sanitized = anonymize(raw_resource, config=deid_rules)

        # 2. Querying fields using the native FHIRPath mini-engine
        resource_id = sanitized.get("id")
        resource_type = sanitized.get("resourceType")

        if resource_type == "Observation":
            loinc_codes = evaluate_fhirpath(sanitized, "code.coding.where(system = 'http://loinc.org').code")
            print(f"Observation {resource_id} LOINC codes: {loinc_codes}")

        records_processed += 1

    return records_processed


if __name__ == "__main__":
    # Simulate a compressed bulk data stream
    sample_ndjson = (
        b'{"resourceType":"Patient","id":"p-101","birthDate":"1982-11-20","name":[{"family":"Smith"}]}\n'
        b'{"resourceType":"Observation","id":"o-202","status":"final","code":{"coding":[{"system":"http://loinc.org","code":"883-9"}]}}\n'
    )

    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode="wb") as gz_file:
        gz_file.write(sample_ndjson)
    compressed_buffer.seek(0)

    # Decompress stream transparently
    with gzip.GzipFile(fileobj=compressed_buffer, mode="rb") as stream_reader:
        total = process_bulk_stream(stream_reader)
    print(f"Successfully processed {total} clinical resources with O(1) memory.")
