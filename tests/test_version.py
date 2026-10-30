"""
Tests for TASK-010: FHIR version profiles (R4 / R4B / R5).

Verifies:
- FHIRVersion enum values and string coercion
- get_fhir_version() returns R4 by default
- set_fhir_version() changes the active version (thread-local)
- fhir_version_context() restores previous version on exit
- fhir_version_context() restores version even on exception
- Thread isolation: each thread has its own version setting
- get_version_info() returns correct structure
- normalize_field() translates R5 aliases to R4 field names
- Top-level fhir_lite exports version API
- Version-aware parsing: R4 Encounter payload with 'class' field
- Version-aware parsing: R5-style Encounter payload with 'class_'
"""

import sys
import threading


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


# ---------------------------------------------------------------------------
# Test 1: FHIRVersion enum
# ---------------------------------------------------------------------------

def test_fhir_version_enum():
    print("\n[1] FHIRVersion enum")
    from fhir_lite.version import FHIRVersion

    check("FHIRVersion.R4 value is 'R4'", FHIRVersion.R4.value == "R4")
    check("FHIRVersion.R4B value is 'R4B'", FHIRVersion.R4B.value == "R4B")
    check("FHIRVersion.R5 value is 'R5'", FHIRVersion.R5.value == "R5")
    check("str(FHIRVersion.R4) == 'R4'", str(FHIRVersion.R4) == "R4")
    check("FHIRVersion('R5') resolves correctly", FHIRVersion("R5") is FHIRVersion.R5)
    check("FHIRVersion is iterable with 3 members", len(list(FHIRVersion)) == 3)


# ---------------------------------------------------------------------------
# Test 2: get/set version
# ---------------------------------------------------------------------------

def test_get_set_version():
    print("\n[2] get_fhir_version / set_fhir_version")
    import fhir_lite
    from fhir_lite.version import FHIRVersion, get_fhir_version, set_fhir_version

    # Default
    set_fhir_version(FHIRVersion.R4)  # reset first
    check("Default version is R4", get_fhir_version() == FHIRVersion.R4)
    check("fhir_lite.get_fhir_version() works at top level", fhir_lite.get_fhir_version() == FHIRVersion.R4)

    # Set by enum
    set_fhir_version(FHIRVersion.R5)
    check("After set R5, get returns R5", get_fhir_version() == FHIRVersion.R5)

    # Set by string
    set_fhir_version("R4B")
    check("set_fhir_version('R4B') works with string", get_fhir_version() == FHIRVersion.R4B)

    # Invalid string
    try:
        set_fhir_version("R9")
        check("Should have raised ValueError for 'R9'", False)
    except ValueError as e:
        check("Raises ValueError for unknown version 'R9'", "R9" in str(e))

    # Restore
    set_fhir_version(FHIRVersion.R4)
    check("Version restored to R4", get_fhir_version() == FHIRVersion.R4)


# ---------------------------------------------------------------------------
# Test 3: context manager
# ---------------------------------------------------------------------------

def test_version_context_manager():
    print("\n[3] fhir_version_context")
    from fhir_lite.version import FHIRVersion, get_fhir_version, set_fhir_version, fhir_version_context
    import fhir_lite

    set_fhir_version(FHIRVersion.R4)

    with fhir_version_context(FHIRVersion.R5) as v:
        check("Inside context: active version is R5", get_fhir_version() == FHIRVersion.R5)
        check("Yielded value is R5", v == FHIRVersion.R5)

    check("After context: version restored to R4", get_fhir_version() == FHIRVersion.R4)

    # Works with string
    with fhir_version_context("R4B"):
        check("Inside context with string 'R4B': active is R4B", get_fhir_version() == FHIRVersion.R4B)
    check("After R4B context: restored to R4", get_fhir_version() == FHIRVersion.R4)

    # Restores even on exception
    try:
        with fhir_version_context(FHIRVersion.R5):
            check("In exception context: version is R5", get_fhir_version() == FHIRVersion.R5)
            raise RuntimeError("deliberate")
    except RuntimeError:
        pass
    check("After exception in context: version still restored to R4", get_fhir_version() == FHIRVersion.R4)

    # top-level alias
    with fhir_lite.fhir_version_context("R5"):
        check("fhir_lite.fhir_version_context works at top level", get_fhir_version() == FHIRVersion.R5)
    check("Restored after top-level context", get_fhir_version() == FHIRVersion.R4)


# ---------------------------------------------------------------------------
# Test 4: thread isolation
# ---------------------------------------------------------------------------

def test_thread_isolation():
    print("\n[4] Thread isolation")
    from fhir_lite.version import FHIRVersion, get_fhir_version, set_fhir_version

    set_fhir_version(FHIRVersion.R4)
    results = {}

    def worker(name: str, ver: FHIRVersion):
        set_fhir_version(ver)
        import time; time.sleep(0.01)  # let other threads run
        results[name] = get_fhir_version()

    t1 = threading.Thread(target=worker, args=("t1", FHIRVersion.R5))
    t2 = threading.Thread(target=worker, args=("t2", FHIRVersion.R4B))
    t1.start(); t2.start()
    t1.join(); t2.join()

    check("Thread t1 saw R5 independently", results.get("t1") == FHIRVersion.R5)
    check("Thread t2 saw R4B independently", results.get("t2") == FHIRVersion.R4B)
    check("Main thread still sees R4 after worker threads", get_fhir_version() == FHIRVersion.R4)


# ---------------------------------------------------------------------------
# Test 5: get_version_info
# ---------------------------------------------------------------------------

def test_get_version_info():
    print("\n[5] get_version_info")
    from fhir_lite.version import FHIRVersion, set_fhir_version, get_version_info
    import fhir_lite

    set_fhir_version(FHIRVersion.R4)
    info = get_version_info()

    check("get_version_info returns dict", isinstance(info, dict))
    check("'active' key present", "active" in info)
    check("'supported' key present", "supported" in info)
    check("'default' key present", "default" in info)
    check("active == 'R4'", info["active"] == "R4")
    check("supported contains R4, R4B, R5", set(info["supported"]) == {"R4", "R4B", "R5"})
    check("default == 'R4'", info["default"] == "R4")
    check("aliases.r5_to_r4 is a dict", isinstance(info.get("aliases", {}).get("r5_to_r4"), dict))

    # top-level alias
    info2 = fhir_lite.get_version_info()
    check("fhir_lite.get_version_info() works at top level", info2["active"] == "R4")


# ---------------------------------------------------------------------------
# Test 6: normalize_field
# ---------------------------------------------------------------------------

def test_normalize_field():
    print("\n[6] normalize_field")
    from fhir_lite.version import FHIRVersion, set_fhir_version, normalize_field

    set_fhir_version(FHIRVersion.R4)
    # In R4 mode: no aliasing
    check("R4: Encounter 'class' unchanged", normalize_field("Encounter", "class") == "class")
    check("R4: Encounter 'class_' unchanged (not in R4 aliases)", normalize_field("Encounter", "class_") == "class_")
    check("R4: unknown resource passthrough", normalize_field("Patient", "name") == "name")

    set_fhir_version(FHIRVersion.R5)
    # In R5 mode: known aliases applied
    check("R5: Encounter 'class_' -> 'class'", normalize_field("Encounter", "class_") == "class")
    check("R5: Unknown field passthrough", normalize_field("Encounter", "status") == "status")
    check("R5: Patient 'name' unchanged", normalize_field("Patient", "name") == "name")

    set_fhir_version(FHIRVersion.R4)


# ---------------------------------------------------------------------------
# Test 7: version-aware resource parsing with R4 payload
# ---------------------------------------------------------------------------

def test_r4_encounter_parsing():
    print("\n[7] R4 Encounter payload parsing")
    from fhir_lite.version import FHIRVersion, fhir_version_context
    from fhir_lite import from_json, Encounter

    r4_json = """{
        "resourceType": "Encounter",
        "id": "enc-r4-001",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "subject": {"reference": "Patient/123"}
    }"""

    with fhir_version_context(FHIRVersion.R4):
        enc = from_json(r4_json)

    check("R4 Encounter: correct type", isinstance(enc, Encounter))
    check("R4 Encounter: id correct", enc.data.get("id") == "enc-r4-001")
    check("R4 Encounter: status is 'finished'", enc.data.get("status") == "finished")
    class_field = enc.data.get("class")
    check("R4 Encounter: 'class' field preserved", isinstance(class_field, dict))


# ---------------------------------------------------------------------------
# Test 8: R5-style payload (permissive parsing)
# ---------------------------------------------------------------------------

def test_r5_encounter_parsing():
    print("\n[8] R5-style Encounter payload (permissive)")
    from fhir_lite.version import FHIRVersion, fhir_version_context
    from fhir_lite import from_json, Encounter

    # R5 uses "class" as well but as a list; we parse permissively
    r5_json = """{
        "resourceType": "Encounter",
        "id": "enc-r5-001",
        "status": "completed",
        "class": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"}],
        "subject": {"reference": "Patient/456"}
    }"""

    with fhir_version_context(FHIRVersion.R5):
        enc = from_json(r5_json)

    check("R5 Encounter: correct type", isinstance(enc, Encounter))
    check("R5 Encounter: id correct", enc.data.get("id") == "enc-r5-001")
    # In R5 'class' is an array; we parsed it as-is (permissive)
    class_field = enc.data.get("class")
    check("R5 Encounter: 'class' field present", class_field is not None)


# ---------------------------------------------------------------------------
# Test 9: top-level API surface
# ---------------------------------------------------------------------------

def test_top_level_api():
    print("\n[9] Top-level fhir_lite version API")
    import fhir_lite

    check("fhir_lite.FHIRVersion accessible", hasattr(fhir_lite, "FHIRVersion"))
    check("fhir_lite.get_fhir_version callable", callable(fhir_lite.get_fhir_version))
    check("fhir_lite.set_fhir_version callable", callable(fhir_lite.set_fhir_version))
    check("fhir_lite.fhir_version_context callable", callable(fhir_lite.fhir_version_context))
    check("fhir_lite.normalize_field callable", callable(fhir_lite.normalize_field))
    check("fhir_lite.get_version_info callable", callable(fhir_lite.get_version_info))

    for name in ("FHIRVersion", "get_fhir_version", "set_fhir_version",
                 "fhir_version_context", "normalize_field", "get_version_info"):
        check(f"'{name}' in fhir_lite.__all__", name in fhir_lite.__all__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_fhir_version_enum,
        test_get_set_version,
        test_version_context_manager,
        test_thread_isolation,
        test_get_version_info,
        test_normalize_field,
        test_r4_encounter_parsing,
        test_r5_encounter_parsing,
        test_top_level_api,
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
    print(f"TASK-010 Version profiles: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("All tests passed! OK")
