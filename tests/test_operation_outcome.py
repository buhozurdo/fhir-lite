"""
Tests for FHIR OperationOutcome resource and FHIRError integration.

Verifies:
- Creation and basic properties (is_valid, is_error, severity, first_text)
- Validation when issue is missing
- Validation with invalid severity or invalid code
- Supported severities and codes
- JSON serialization and deserialization roundtrip
- XML serialization and deserialization roundtrip
- Polymorphic instantiation via FHIRResource.from_json / from_xml
- Integration with FHIRError
- Multiple issues handling
"""

import sys
from fhir_lite import (
    OperationOutcome,
    FHIRResource,
    FHIRError,
    from_json,
    from_xml,
)


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


def test_basic_creation():
    print("\n[1] Basic OperationOutcome creation")
    outcome = OperationOutcome({
        "issue": [{
            "severity": "error",
            "code": "not-found",
            "diagnostics": "Resource Patient/123 was not found."
        }]
    })

    check("Resource type is OperationOutcome", outcome.resource_type == "OperationOutcome")
    check("data has resourceType OperationOutcome", outcome.data.get("resourceType") == "OperationOutcome")
    check("is_valid is True", outcome.is_valid)
    check("is_error is True for severity 'error'", outcome.is_error)
    check("severity returns 'error'", outcome.severity == "error")
    check("first_text returns diagnostics", outcome.first_text() == "Resource Patient/123 was not found.")
    check("issues length is 1", len(outcome.issues) == 1)


def test_validation_no_issues():
    print("\n[2] Validation without issues")
    outcome = OperationOutcome()
    errors = outcome.validate()
    check("Invalid when no issue array", not outcome.is_valid)
    check("Error message specifies missing issue", any("requires at least one 'issue'" in e for e in errors))


def test_validation_invalid_severity():
    print("\n[3] Validation with invalid severity")
    outcome = OperationOutcome({
        "issue": [{"severity": "critical", "code": "processing"}]
    })
    check("is_valid is False for non-standard severity", not outcome.is_valid)
    errors = outcome.validate()
    check("Validation reports invalid severity", any("invalid severity 'critical'" in e for e in errors))


def test_validation_invalid_code():
    print("\n[4] Validation with invalid code")
    outcome = OperationOutcome({
        "issue": [{"severity": "error", "code": "exploded"}]
    })
    check("is_valid is False for non-standard code", not outcome.is_valid)
    errors = outcome.validate()
    check("Validation reports invalid code", any("invalid code 'exploded'" in e for e in errors))


def test_valid_severities():
    print("\n[5] Valid severities and is_error behavior")
    for sev in ["fatal", "error"]:
        oo = OperationOutcome({"issue": [{"severity": sev, "code": "processing"}]})
        check(f"Severity '{sev}' is valid", oo.is_valid)
        check(f"Severity '{sev}' triggers is_error=True", oo.is_error)

    for sev in ["warning", "information"]:
        oo = OperationOutcome({"issue": [{"severity": sev, "code": "informational"}]})
        check(f"Severity '{sev}' is valid", oo.is_valid)
        check(f"Severity '{sev}' leaves is_error=False", not oo.is_error)


def test_json_roundtrip():
    print("\n[6] JSON serialization roundtrip")
    original = OperationOutcome({
        "id": "outcome-01",
        "issue": [{
            "severity": "warning",
            "code": "transient",
            "diagnostics": "Server under temporary load",
            "details": {"text": "Temporary load"}
        }]
    })

    json_str = original.to_json()
    reconstructed = from_json(json_str)

    check("Reconstructed is OperationOutcome", isinstance(reconstructed, OperationOutcome))
    check("id matches", reconstructed.data.get("id") == "outcome-01")
    check("issues count matches", len(reconstructed.issues) == 1)
    check("diagnostics matches", reconstructed.first_text() == "Server under temporary load")


def test_xml_roundtrip():
    print("\n[7] XML serialization roundtrip")
    original = OperationOutcome({
        "id": "outcome-02",
        "issue": [{
            "severity": "error",
            "code": "invalid",
            "diagnostics": "Field name is required"
        }]
    })

    xml_str = original.to_xml()
    reconstructed = from_xml(xml_str)

    check("Reconstructed from XML is OperationOutcome", isinstance(reconstructed, OperationOutcome))
    check("id matches", reconstructed.data.get("id") == "outcome-02")
    check("severity matches", reconstructed.severity == "error")
    check("first_text matches", reconstructed.first_text() == "Field name is required")


def test_from_json_dispatch():
    print("\n[8] Polymorphic instantiation via FHIRResource")
    raw = '{"resourceType": "OperationOutcome", "issue": [{"severity": "fatal", "code": "security"}]}'
    res = FHIRResource.from_json(raw)
    check("Dispatch returns OperationOutcome instance", isinstance(res, OperationOutcome))
    check("severity is fatal", res.severity == "fatal")


def test_fhir_error_outcome_property():
    print("\n[9] FHIRError integration with OperationOutcome")
    outcome = OperationOutcome({
        "issue": [{
            "severity": "error",
            "code": "forbidden",
            "diagnostics": "Access token expired"
        }]
    })
    err = FHIRError(403, "Forbidden", outcome=outcome)

    check("err.status_code is 403", err.status_code == 403)
    check("err.outcome is OperationOutcome", isinstance(err.outcome, OperationOutcome))
    check("err.outcome.is_error is True", err.outcome.is_error)
    check("err.outcome.first_text() matches", err.outcome.first_text() == "Access token expired")


def test_multiple_issues():
    print("\n[10] Multiple issues handling")
    outcome = OperationOutcome({
        "issue": [
            {"severity": "warning", "code": "incomplete", "diagnostics": "Postal code missing"},
            {"severity": "error", "code": "required", "diagnostics": "Family name is mandatory"}
        ]
    })

    check("is_valid with multiple valid issues", outcome.is_valid)
    check("len(issues) == 2", len(outcome.issues) == 2)
    check("first severity is 'warning'", outcome.severity == "warning")
    check("is_error is True because of second issue", outcome.is_error)
    check("first_text returns first issue diagnostics", outcome.first_text() == "Postal code missing")


if __name__ == "__main__":
    tests = [
        test_basic_creation,
        test_validation_no_issues,
        test_validation_invalid_severity,
        test_validation_invalid_code,
        test_valid_severities,
        test_json_roundtrip,
        test_xml_roundtrip,
        test_from_json_dispatch,
        test_fhir_error_outcome_property,
        test_multiple_issues,
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
    print(f"OperationOutcome: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("All tests passed! OK")
