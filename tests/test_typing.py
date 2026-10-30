"""
Tests for TASK-008: py.typed marker and TypedDict definitions.

Verifies:
- py.typed marker file exists in the package directory
- fhir_lite.types exports all expected TypedDict classes
- TypedDicts are usable at runtime (dict-compatible)
- __all__ in __init__ includes all TypedDict names
- All TypedDicts are importable directly from fhir_lite
"""

import importlib
import importlib.util
import os
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


# ---------------------------------------------------------------------------
# Test: py.typed marker
# ---------------------------------------------------------------------------

def test_py_typed_exists():
    print("\n[1] py.typed marker")
    import fhir_lite
    pkg_dir = os.path.dirname(fhir_lite.__file__)
    marker = os.path.join(pkg_dir, "py.typed")
    check("py.typed file exists in fhir_lite package directory", os.path.isfile(marker))


# ---------------------------------------------------------------------------
# Test: fhir_lite.types module exports
# ---------------------------------------------------------------------------

EXPECTED_TYPES = [
    "ExtensionDict",
    "CodingDict",
    "CodeableConceptDict",
    "ReferenceDict",
    "QuantityDict",
    "PeriodDict",
    "IdentifierDict",
    "HumanNameDict",
    "ContactPointDict",
    "AddressDict",
    "MetaDict",
    "BundleEntryDict",
    "BundleEntryRequestDict",
    "BundleEntryResponseDict",
    "DosageDict",
    "NarrativeDict",
    "IssueDict",
]


def test_types_module_exports():
    print("\n[2] fhir_lite.types exports")
    from fhir_lite import types as ft
    for name in EXPECTED_TYPES:
        check(f"fhir_lite.types.{name} is defined", hasattr(ft, name))

    check("__all__ in types.py covers all expected names",
          all(n in ft.__all__ for n in EXPECTED_TYPES))


# ---------------------------------------------------------------------------
# Test: TypedDicts usable at runtime
# ---------------------------------------------------------------------------

def test_typeddicts_runtime_usage():
    print("\n[3] TypedDict runtime usage")
    from fhir_lite.types import (
        CodingDict, CodeableConceptDict, IdentifierDict,
        HumanNameDict, BundleEntryDict, ReferenceDict,
    )

    coding: CodingDict = {"system": "http://loinc.org", "code": "8480-6", "display": "Systolic BP"}
    check("CodingDict instantiates as plain dict", isinstance(coding, dict))
    check("CodingDict has expected keys", coding["system"] == "http://loinc.org")

    concept: CodeableConceptDict = {"coding": [coding], "text": "Systolic Blood Pressure"}
    check("CodeableConceptDict with nested CodingDict", isinstance(concept["coding"], list))

    name: HumanNameDict = {"use": "official", "family": "Smith", "given": ["John"]}
    check("HumanNameDict given is a list", isinstance(name["given"], list))

    identifier: IdentifierDict = {"system": "http://hospital.example.org", "value": "12345"}
    check("IdentifierDict instantiates correctly", identifier["value"] == "12345")

    entry: BundleEntryDict = {
        "fullUrl": "urn:uuid:abc123",
        "resource": {"resourceType": "Patient"},
    }
    check("BundleEntryDict with resource dict", entry["resource"]["resourceType"] == "Patient")

    ref: ReferenceDict = {"reference": "Patient/123", "display": "John Smith"}
    check("ReferenceDict instantiates correctly", ref["reference"] == "Patient/123")


# ---------------------------------------------------------------------------
# Test: fhir_lite top-level imports
# ---------------------------------------------------------------------------

def test_top_level_imports():
    print("\n[4] Top-level fhir_lite imports")
    import fhir_lite
    for name in EXPECTED_TYPES:
        check(f"fhir_lite.{name} accessible at top level", hasattr(fhir_lite, name))
    for name in EXPECTED_TYPES:
        check(f"'{name}' in fhir_lite.__all__", name in fhir_lite.__all__)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_py_typed_exists,
        test_types_module_exports,
        test_typeddicts_runtime_usage,
        test_top_level_imports,
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
    print(f"TASK-008 Typing: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("All tests passed! OK")
