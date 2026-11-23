"""Performance benchmark suite for fhir-lite.

Measures import latency, allocation overhead, and throughput
for core serialization, bundle traversal, and FHIRPath queries.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path
from typing import Callable, Any

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def time_execution(fn: Callable[[], Any], iterations: int = 1000) -> float:
    """Measure average execution time per iteration in microseconds."""
    gc.collect()
    gc.disable()
    try:
        start = time.perf_counter_ns()
        for _ in range(iterations):
            fn()
        elapsed_ns = time.perf_counter_ns() - start
        return (elapsed_ns / iterations) / 1000.0
    finally:
        gc.enable()


def benchmark_core_operations() -> dict[str, float]:
    """Execute benchmarks for foundational library primitives."""
    from fhir_lite import Patient, Observation, Bundle, evaluate_fhirpath, json_to_xml, xml_to_json

    results: dict[str, float] = {}

    # 1. Single Resource Instantiation
    def test_patient_instantiation() -> None:
        Patient(
            id="bench-pat-01",
            active=True,
            gender="female",
            birthDate="1985-04-12",
            name=[{"use": "official", "family": "Smith", "given": ["Jane"]}],
        )

    results["patient_instantiation_us"] = time_execution(test_patient_instantiation, iterations=2000)

    # 2. JSON to XML Conversion
    sample_json = (
        '{"resourceType":"Patient","id":"p1","active":true,"gender":"male",'
        '"birthDate":"1990-01-01","name":[{"family":"Doe","given":["John"]}]}'
    )

    def test_json_to_xml() -> None:
        json_to_xml(sample_json, pretty=False)

    results["json_to_xml_us"] = time_execution(test_json_to_xml, iterations=2000)

    # 3. XML to JSON Conversion
    sample_xml = json_to_xml(sample_json, pretty=False)

    def test_xml_to_json() -> None:
        xml_to_json(sample_xml)

    results["xml_to_json_us"] = time_execution(test_xml_to_json, iterations=2000)

    # 4. Large Bundle Creation (500 entries)
    raw_entries = [
        {
            "resource": {
                "resourceType": "Observation",
                "id": f"obs-{i}",
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "883-9"}]},
                "valueQuantity": {"value": 120.0 + (i % 20), "unit": "mmHg"},
            }
        }
        for i in range(500)
    ]
    bundle = Bundle(entry=raw_entries)

    # 5. Lazy Resource Filtering
    def test_lazy_filter() -> None:
        list(bundle.iter_resources_by_type("Observation"))

    results["bundle_500_lazy_filter_us"] = time_execution(test_lazy_filter, iterations=500)

    # 6. FHIRPath Query
    def test_fhirpath() -> None:
        evaluate_fhirpath(bundle.data, "entry.resource.where(status = 'final').id")

    results["fhirpath_evaluation_us"] = time_execution(test_fhirpath, iterations=500)

    return results


def main() -> None:
    print("=" * 60)
    print(" fhir-lite Performance Benchmark")
    print(f" Python: {sys.version.split()[0]} | Platform: {sys.platform}")
    print("=" * 60)

    metrics = benchmark_core_operations()
    for metric_name, value_us in metrics.items():
        print(f" - {metric_name:<30}: {value_us:8.2f} us")
    print("=" * 60)


if __name__ == "__main__":
    main()
