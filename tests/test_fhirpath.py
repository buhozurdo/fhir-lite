"""Tests for TASK-024: Native Zero-Dependency FHIRPath Mini-Engine.
"""

import pytest
from fhir_lite import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
    evaluate_fhirpath,
    FHIRPathError,
)


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


def test_basic_path_traversal():
    print("Testing basic path traversal...")
    patient = Patient(
        id="pat-101",
        active=True,
        gender="female",
        name=[
            {"use": "official", "family": "Smith", "given": ["Jane", "Marie"]},
            {"use": "nickname", "family": "Doe", "given": ["Janie"]},
        ],
        telecom=[
            {"system": "phone", "value": "555-1234"},
            {"system": "email", "value": "jane@example.com"},
        ],
    )

    # 1. Top-level scalar property
    res = evaluate_fhirpath(patient, "gender")
    check("gender scalar", res == ["female"])

    # 2. Resource type prefix tolerance
    check("Patient.gender", evaluate_fhirpath(patient, "Patient.gender") == ["female"])

    # 3. Array property projection (flattens automatically)
    check("name.family", evaluate_fhirpath(patient, "name.family") == ["Smith", "Doe"])
    check("name.given", evaluate_fhirpath(patient, "name.given") == ["Jane", "Marie", "Janie"])

    # 4. Nested dict traversal
    check("telecom.value", evaluate_fhirpath(patient, "telecom.value") == ["555-1234", "jane@example.com"])

    # 5. Missing fields return empty list
    check("missing field", evaluate_fhirpath(patient, "birthDate") == [])
    check("deep missing field", evaluate_fhirpath(patient, "contact.name.family") == [])


def test_first_last_and_indexing():
    print("Testing first(), last(), and index access...")
    patient = Patient(
        id="pat-102",
        name=[
            {"use": "official", "family": "Smith", "given": ["Jane"]},
            {"use": "nickname", "family": "Doe", "given": ["JD"]},
        ],
    )

    # 1. first()
    check("name.first().family", evaluate_fhirpath(patient, "name.first().family") == ["Smith"])

    # 2. last()
    check("name.last().family", evaluate_fhirpath(patient, "name.last().family") == ["Doe"])

    # 3. Index notation [0], [1]
    check("name[0].family", evaluate_fhirpath(patient, "name[0].family") == ["Smith"])
    check("name[1].family", evaluate_fhirpath(patient, "name[1].family") == ["Doe"])
    check("name[99].family out of range", evaluate_fhirpath(patient, "name[99].family") == [])

    # 4. first parameter in evaluate_fhirpath
    check("first=True returns single scalar", evaluate_fhirpath(patient, "name.first().family", first=True) == "Smith")
    check("first=True on empty returns None", evaluate_fhirpath(patient, "missing.field", first=True) is None)


def test_where_filtering():
    print("Testing .where(...) filtering...")
    patient = Patient(
        id="pat-103",
        name=[
            {"use": "official", "family": "Smith", "given": ["Jane"]},
            {"use": "nickname", "family": "Doe", "given": ["Janie"]},
        ],
        telecom=[
            {"system": "phone", "value": "555-1234", "use": "home"},
            {"system": "phone", "value": "555-9999", "use": "work"},
            {"system": "email", "value": "jane@example.com", "use": "home"},
        ],
    )

    # 1. Simple equality filter
    official_family = evaluate_fhirpath(patient, "name.where(use = 'official').family")
    check("name.where(use = 'official').family", official_family == ["Smith"])

    # 2. Inequality filter
    non_official = evaluate_fhirpath(patient, "name.where(use != 'official').family")
    check("name.where(use != 'official').family", non_official == ["Doe"])

    # 3. Binary logical AND in where
    work_phone = evaluate_fhirpath(patient, "telecom.where(system = 'phone' and use = 'work').value")
    check("telecom.where(system = 'phone' and use = 'work').value", work_phone == ["555-9999"])

    # 4. Binary logical OR in where
    home_contacts = evaluate_fhirpath(patient, "telecom.where(use = 'home' or system = 'email').value")
    check("telecom.where(use = 'home' or system = 'email').value", home_contacts == ["555-1234", "jane@example.com"])


def test_exists_and_empty():
    print("Testing exists() and empty()...")
    patient = Patient(
        id="pat-104",
        name=[{"family": "Smith"}],
        telecom=[{"system": "phone", "value": "555-1111"}],
    )

    # 1. exists() without args
    check("name.exists()", evaluate_fhirpath(patient, "name.exists()") == [True])
    check("address.exists()", evaluate_fhirpath(patient, "address.exists()") == [False])

    # 2. exists(criteria)
    check("telecom.exists(system = 'phone')", evaluate_fhirpath(patient, "telecom.exists(system = 'phone')") == [True])
    check("telecom.exists(system = 'fax')", evaluate_fhirpath(patient, "telecom.exists(system = 'fax')") == [False])

    # 3. empty()
    check("name.empty()", evaluate_fhirpath(patient, "name.empty()") == [False])
    check("address.empty()", evaluate_fhirpath(patient, "address.empty()") == [True])


def test_collection_operators():
    print("Testing count(), skip(), take(), tail(), distinct()...")
    data = {
        "items": [10, 20, 30, 40, 20, 10]
    }

    check("items.count()", evaluate_fhirpath(data, "items.count()") == [6])
    check("items.skip(2)", evaluate_fhirpath(data, "items.skip(2)") == [30, 40, 20, 10])
    check("items.take(3)", evaluate_fhirpath(data, "items.take(3)") == [10, 20, 30])
    check("items.tail()", evaluate_fhirpath(data, "items.tail()") == [20, 30, 40, 20, 10])
    check("items.distinct()", evaluate_fhirpath(data, "items.distinct()") == [10, 20, 30, 40])


def test_string_functions():
    print("Testing string functions (contains, startsWith, endsWith, lower, upper, join)...")
    patient = Patient(
        name=[
            {"family": "Van Der Berg", "given": ["Jan", "Karel"]},
        ]
    )

    check("contains", evaluate_fhirpath(patient, "name.family.contains('Der')") == [True])
    check("startsWith", evaluate_fhirpath(patient, "name.family.startsWith('Van')") == [True])
    check("endsWith", evaluate_fhirpath(patient, "name.family.endsWith('Berg')") == [True])
    check("lower", evaluate_fhirpath(patient, "name.family.lower()") == ["van der berg"])
    check("upper", evaluate_fhirpath(patient, "name.family.upper()") == ["VAN DER BERG"])
    check("join", evaluate_fhirpath(patient, "name.given.join(', ')") == ["Jan, Karel"])


def test_bundle_evaluation():
    print("Testing complex bundle traversal...")
    bundle = Bundle(
        type="searchset",
        entry=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "name": [{"family": "Doe"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "o1",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "883-9"}]},
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "o2",
                    "status": "preliminary",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7"}]},
                }
            },
        ],
    )

    # 1. Filter bundle entries by resourceType
    obs_statuses = evaluate_fhirpath(
        bundle, "entry.resource.where(resourceType = 'Observation').status"
    )
    check("bundle observation status", obs_statuses == ["final", "preliminary"])

    # 2. Filter by observation status and extract LOINC code
    final_loinc = evaluate_fhirpath(
        bundle,
        "entry.resource.where(resourceType = 'Observation' and status = 'final').code.coding.code",
    )
    check("final observation loinc code", final_loinc == ["883-9"])


def test_resource_method_integration():
    print("Testing resource.fhirpath() method integration...")
    patient = Patient(
        id="pat-direct",
        name=[{"use": "official", "family": "Newton", "given": ["Isaac"]}],
        telecom=[{"system": "phone", "value": "123-4567"}],
    )

    check("patient.fhirpath", patient.fhirpath("name.where(use = 'official').family") == ["Newton"])
    check("patient.fhirpath first=True", patient.fhirpath("name.first().family", first=True) == "Newton")
    check("patient.fhirpath phone", patient.fhirpath("telecom.where(system = 'phone').value", first=True) == "123-4567")


def test_comparisons_and_literals():
    print("Testing comparisons, numbers, and boolean literals...")
    data = {
        "measurements": [
            {"value": 10, "unit": "mg", "valid": True},
            {"value": 25.5, "unit": "mg", "valid": False},
            {"value": 50, "unit": "mg", "valid": True},
        ]
    }

    # Comparisons
    check(">", evaluate_fhirpath(data, "measurements.where(value > 20).value") == [25.5, 50])
    check(">=", evaluate_fhirpath(data, "measurements.where(value >= 25.5).value") == [25.5, 50])
    check("<", evaluate_fhirpath(data, "measurements.where(value < 20).value") == [10])
    check("<=", evaluate_fhirpath(data, "measurements.where(value <= 25.5).value") == [10, 25.5])
    check("bool true", evaluate_fhirpath(data, "measurements.where(valid = true).value") == [10, 50])
    check("bool false", evaluate_fhirpath(data, "measurements.where(valid = false).value") == [25.5])
    check("!=", evaluate_fhirpath(data, "measurements.where(value != 10).value") == [25.5, 50])
    check("contains binary op", evaluate_fhirpath({"tags": ["urgent", "lab"]}, "tags contains 'urgent'") == [True])
    check("contains binary op str", evaluate_fhirpath({"name": "Emergency Room"}, "name contains 'gency'") == [True])


def test_as_and_not():
    print("Testing .as() and .not() functions...")
    entries = [
        {"resourceType": "Observation", "id": "obs1"},
        {"resourceType": "Condition", "id": "cond1"},
    ]
    check(".as(Observation)", evaluate_fhirpath(entries, "as(Observation).id") == ["obs1"])
    check(".as(Condition)", evaluate_fhirpath(entries, "as(Condition).id") == ["cond1"])
    check(".not() on false", evaluate_fhirpath({"active": False}, "active.not()") == [True])
    check(".not() on true", evaluate_fhirpath({"active": True}, "active.not()") == [False])


def test_edge_cases():
    print("Testing edge cases and empty expressions...")
    check("empty expression", evaluate_fhirpath({"a": 1}, "") == [])
    check("empty expression first=True", evaluate_fhirpath({"a": 1}, "   ", first=True) is None)
    check("whitespace handling", evaluate_fhirpath({"a": 42}, "  a  ") == [42])

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "where()")  # missing criteria

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "skip()")  # missing argument

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "take()")  # missing argument

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "contains()")  # missing argument

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "startsWith()")  # missing argument

    with pytest.raises(FHIRPathError):
        evaluate_fhirpath({"a": 1}, "endsWith()")  # missing argument


if __name__ == "__main__":
    test_basic_path_traversal()
    test_first_last_and_indexing()
    test_where_filtering()
    test_exists_and_empty()
    test_collection_operators()
    test_string_functions()
    test_bundle_evaluation()
    test_resource_method_integration()
    test_comparisons_and_literals()
    test_as_and_not()
    test_edge_cases()
    test_fhirpath_errors()
    print("\nAll FHIRPath tests PASSED successfully!")
