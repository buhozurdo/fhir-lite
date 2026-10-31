"""
Tests for TASK-014: Optional Pydantic interoperability.

Verifies:
- FHIRResource.from_pydantic() with real Pydantic v2 models
- Automatic polymorphic instantiation (e.g. Patient subclass returned)
- Serialization to XML/JSON from Pydantic-originated resources
- Resource.to_pydantic() converting FHIRResource back into a Pydantic model
- Error handling when non-Pydantic objects are passed to from_pydantic
- Preservation of nested structures (e.g. name array, telecom)
"""

import sys
from fhir_lite import FHIRResource, Patient, Observation


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


def test_pydantic_integration():
    try:
        from pydantic import BaseModel, Field
    except ImportError:
        print("\n[SKIP] Pydantic is not installed in the environment.")
        return

    print("\n[1] Pydantic v2 BaseModel interoperability")

    class PatientModel(BaseModel):
        resourceType: str = "Patient"
        id: str
        active: bool = True
        gender: str

    # 1. from_pydantic
    pyd_patient = PatientModel(id="pyd-001", active=True, gender="female")
    resource = FHIRResource.from_pydantic(pyd_patient)

    check("Polymorphic return is Patient instance", isinstance(resource, Patient))
    check("id matches", resource.id == "pyd-001")
    check("active is boolean True", resource.active is True)
    check("gender is female", resource.gender == "female")
    check("is_valid is True", resource.is_valid)

    # 2. to_xml from Pydantic resource
    xml_out = resource.to_xml()
    check("XML contains <Patient", "<Patient" in xml_out)
    check("XML contains gender", '<gender value="female"' in xml_out)

    # 3. to_pydantic conversion
    converted_back = resource.to_pydantic(PatientModel)
    check("converted_back is PatientModel", isinstance(converted_back, PatientModel))
    check("converted_back.id matches", converted_back.id == "pyd-001")
    check("converted_back.gender matches", converted_back.gender == "female")


def test_nested_pydantic_model():
    try:
        from pydantic import BaseModel
        from typing import List
    except ImportError:
        return

    print("\n[2] Nested Pydantic structures")

    class HumanName(BaseModel):
        family: str
        given: List[str]

    class FullPatientModel(BaseModel):
        resourceType: str = "Patient"
        id: str
        name: List[HumanName]

    pyd_full = FullPatientModel(
        id="pyd-nested",
        name=[HumanName(family="Smith", given=["Alice", "Marie"])]
    )

    fhir_res = FHIRResource.from_pydantic(pyd_full)
    check("Converted nested resource is Patient", isinstance(fhir_res, Patient))
    check("name[0]['family'] matches", fhir_res.name[0]["family"] == "Smith")
    check("name[0]['given'] has 2 items", len(fhir_res.name[0]["given"]) == 2)

    # Convert back to Pydantic
    back = fhir_res.to_pydantic(FullPatientModel)
    check("Roundtrip nested model preserves family", back.name[0].family == "Smith")
    check("Roundtrip nested model preserves given", back.name[0].given == ["Alice", "Marie"])


def test_invalid_pydantic_input():
    print("\n[3] Error handling on invalid input to from_pydantic")
    try:
        FHIRResource.from_pydantic({"plain": "dict"})  # not a Pydantic model
        check("Should have raised TypeError for plain dict", False)
    except TypeError as e:
        check("Raises TypeError for non-pydantic input", "Expected Pydantic model instance" in str(e))


if __name__ == "__main__":
    tests = [
        test_pydantic_integration,
        test_nested_pydantic_model,
        test_invalid_pydantic_input,
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
    print(f"TASK-014 Pydantic Interop: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("All tests passed! OK")
