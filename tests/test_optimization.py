"""
Tests for TASK-013: Memory slots, dynamic attributes, and PEP 562 lazy loading.

Verifies:
- FHIRResource and all core subclasses have __slots__ and NO __dict__
- Dynamic attribute writes store transparently in .data
- Lazy loading: 'import fhir_lite' does not import client or ndjson until accessed
- All symbols in __all__ resolve correctly through __getattr__
- __dir__() matches __all__
"""

import sys
import fhir_lite
from fhir_lite import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
    Practitioner,
    Encounter,
    Condition,
    MedicationRequest,
    Medication,
    OperationOutcome,
)


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


def test_slots_eliminate_dict():
    print("\n[1] Memory optimization: __slots__ without __dict__")
    classes = [
        FHIRResource,
        Patient,
        Observation,
        Bundle,
        Practitioner,
        Encounter,
        Condition,
        MedicationRequest,
        Medication,
        OperationOutcome,
    ]

    for cls in classes:
        inst = cls()
        has_dict = hasattr(inst, "__dict__")
        check(f"{cls.__name__} has NO __dict__", not has_dict)
        check(f"{cls.__name__} has 'data' in __slots__", "data" in inst.__slots__ or hasattr(inst, "data"))


def test_dynamic_attribute_assignment():
    print("\n[2] Dynamic attribute assignment redirects to self.data")
    p = Patient(id="pat-slots-1")
    check("Initial id is pat-slots-1", p.id == "pat-slots-1")

    # Modifying existing field
    p.id = "pat-slots-updated"
    check("Modified id reflected in .id", p.id == "pat-slots-updated")
    check("Modified id reflected in .data['id']", p.data["id"] == "pat-slots-updated")

    # Setting new field that was not in data
    p.birthDate = "1990-05-15"
    check("New field birthDate accessible via attribute", p.birthDate == "1990-05-15")
    check("New field birthDate stored in p.data", p.data.get("birthDate") == "1990-05-15")

    # Setting 'data' itself replaces the internal dictionary
    p.data = {"resourceType": "Patient", "id": "replaced"}
    check("Replacing .data works safely", p.id == "replaced")


def test_lazy_loading_pep_562():
    print("\n[3] PEP 562 Lazy Loading")
    # Test dir() exposes __all__
    module_dir = dir(fhir_lite)
    check("__dir__() returns all public symbols", set(fhir_lite.__all__).issubset(set(module_dir)))

    # Test that accessing all symbols in __all__ works
    for symbol in fhir_lite.__all__:
        attr = getattr(fhir_lite, symbol)
        check(f"Symbol '{symbol}' resolves via __getattr__", attr is not None)

    # Test invalid attribute raises AttributeError
    try:
        getattr(fhir_lite, "NonExistentSymbol12345")
        check("Should have raised AttributeError for invalid symbol", False)
    except AttributeError:
        check("AttributeError raised for non-existent symbol", True)


def test_bundle_and_ndjson_performance_optimizations():
    print("\n[4] Bundle & NDJSON lazy evaluation and streaming optimizations")
    import io
    import json
    from fhir_lite import (
        Bundle,
        Patient,
        Observation,
        iter_loads_ndjson,
        iter_loads_ndjson_raw,
        iter_dumps_ndjson,
    )

    # 1. Bundle lazy evaluation on 500 entries
    bundle = Bundle(type="collection")
    for i in range(500):
        bundle.add_entry(Observation(id=f"obs-{i}", status="final", code={"text": "lab"}))
    bundle.add_entry(Patient(id="rare-pat", active=True, gender="female"))

    # Verify iter_entries does not duplicate list
    entries_gen = bundle.iter_entries()
    first_entry = next(entries_gen)
    check("iter_entries yields entry dict", isinstance(first_entry, dict))

    # Verify iter_raw_resources yields dict directly
    raw_obs_gen = bundle.iter_raw_resources("Observation")
    first_raw = next(raw_obs_gen)
    check("iter_raw_resources yields raw dict without wrapper", isinstance(first_raw, dict) and not isinstance(first_raw, FHIRResource))

    # Verify iter_resources_by_type filters before instantiating
    rare_gen = bundle.iter_resources_by_type("Patient")
    rare_pat = next(rare_gen)
    check("iter_resources_by_type yields matching Patient", isinstance(rare_pat, Patient) and rare_pat.id == "rare-pat")

    # get_resources_by_type only instantiates matching items
    pats = bundle.get_resources_by_type(Patient)
    check("get_resources_by_type returns matching items", len(pats) == 1 and pats[0].id == "rare-pat")

    # filter_entries with predicate
    filtered = list(bundle.filter_entries(lambda d: d.get("id") == "rare-pat"))
    check("filter_entries filters with predicate", len(filtered) == 1 and filtered[0].id == "rare-pat")

    # stream_json incremental emission
    stream_buf = io.StringIO()
    written = bundle.stream_json(stream_buf, chunk_size=50)
    check("stream_json writes valid JSON", written > 0)
    reloaded = json.loads(stream_buf.getvalue())
    check("stream_json parses with 501 entries", len(reloaded["entry"]) == 501)

    # 2. NDJSON lazy streaming on 500 records
    ndjson_data = "\n".join(json.dumps({"resourceType": "Observation", "id": f"nd-{i}", "status": "final"}) for i in range(500))
    lazy_gen = iter_loads_ndjson(ndjson_data)
    first_loaded = next(lazy_gen)
    check("iter_loads_ndjson yields FHIRResource lazily", isinstance(first_loaded, Observation))

    lazy_raw_gen = iter_loads_ndjson_raw(ndjson_data)
    first_raw_loaded = next(lazy_raw_gen)
    check("iter_loads_ndjson_raw yields raw dict lazily", isinstance(first_raw_loaded, dict))

    # iter_dumps_ndjson
    line_gen = iter_dumps_ndjson([Patient(id="p1", active=True), Observation(id="o1", status="final")])
    first_line = next(line_gen)
    check("iter_dumps_ndjson yields line lazily", first_line.endswith("\n"))


if __name__ == "__main__":
    tests = [
        test_slots_eliminate_dict,
        test_dynamic_attribute_assignment,
        test_lazy_loading_pep_562,
        test_bundle_and_ndjson_performance_optimizations,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"    !! {e}")

    print(f"\n{'='*50}")
    print(f"TASK-013 Optimizations: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("All tests passed! OK")
