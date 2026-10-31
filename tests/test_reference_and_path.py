"""
Tests for TASK / v0.1.2: Safe Path Traversal (get_path) and Reference Helper.
"""

from fhir_lite import Patient, Observation, Reference, FHIRResource


def check(description: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}")
    if not condition:
        raise AssertionError(f"Assertion failed: {description}")


def test_get_path():
    print("Testing get_path()...")
    patient = Patient(
        id="pat-100",
        active=True,
        gender="female",
        name=[
            {"use": "official", "family": "Smith", "given": ["Jane", "Marie"]},
            {"use": "nickname", "given": ["Janie"]},
        ],
        telecom=[
            {"system": "phone", "value": "555-1234"}
        ],
    )

    # 1. Top-level keys
    check("get_path id", patient.get_path("id") == "pat-100")
    check("get_path active", patient.get_path("active") is True)
    check("get_path gender", patient.get_path("gender") == "female")

    # 2. Nested dict and list indices with dot notation
    check("get_path name.0.family", patient.get_path("name.0.family") == "Smith")
    check("get_path name.0.given.0", patient.get_path("name.0.given.0") == "Jane")
    check("get_path name.0.given.1", patient.get_path("name.0.given.1") == "Marie")
    check("get_path name.1.use", patient.get_path("name.1.use") == "nickname")
    check("get_path telecom.0.value", patient.get_path("telecom.0.value") == "555-1234")

    # 3. List/tuple path parameter
    check("get_path sequence", patient.get_path(["name", 0, "family"]) == "Smith")
    check("get_path sequence with int", patient.get_path(["name", 0, "given", 1]) == "Marie")

    # 4. Defaults on missing or out-of-bounds keys
    check("get_path non-existent key default", patient.get_path("birthDate") is None)
    check("get_path non-existent with custom default", patient.get_path("birthDate", default="1990-01-01") == "1990-01-01")
    check("get_path out of bounds index", patient.get_path("name.99.family", default="N/A") == "N/A")
    check("get_path invalid index string", patient.get_path("name.abc.family", default="ERR") == "ERR")
    check("get_path traversal past leaf", patient.get_path("id.subfield", default="LEAF") == "LEAF")
    check("get_path invalid path argument", patient.get_path(12345, default="BAD") == "BAD")

    # 5. Complex observation nesting
    obs = Observation(
        status="final",
        code={
            "coding": [
                {"system": "http://loinc.org", "code": "883-9", "display": "ABO group"}
            ]
        }
    )
    check("obs loinc code", obs.get_path("code.coding.0.code") == "883-9")
    check("obs loinc system", obs.get_path("code.coding.0.system") == "http://loinc.org")


def test_reference():
    print("Testing Reference helper...")

    # 1. Parsing relative string
    ref1 = Reference.parse("Patient/12345")
    check("parse relative resource_type", ref1.resource_type == "Patient")
    check("parse relative id", ref1.id == "12345")
    check("parse relative reference", ref1.reference == "Patient/12345")
    check("parse relative display is None", ref1.display is None)

    # 2. Parsing absolute URL
    ref2 = Reference.parse("https://hapi.fhir.org/baseR4/Observation/obs-99")
    check("parse absolute resource_type", ref2.resource_type == "Observation")
    check("parse absolute id", ref2.id == "obs-99")

    # 3. Parsing dictionary
    ref_dict = {"reference": "Condition/cond-1", "display": "Hypertension"}
    ref3 = Reference.parse(ref_dict)
    check("parse dict resource_type", ref3.resource_type == "Condition")
    check("parse dict id", ref3.id == "cond-1")
    check("parse dict display", ref3.display == "Hypertension")

    # 4. Parsing fragment reference (#contained)
    ref4 = Reference.parse("#local-practitioner")
    check("parse fragment reference", ref4.reference == "#local-practitioner")
    check("parse fragment id", ref4.id == "local-practitioner")
    check("parse fragment resource_type", ref4.resource_type is None)

    # 5. Empty and edge cases
    ref_empty = Reference.parse("")
    check("parse empty reference", ref_empty.reference == "")

    try:
        Reference.parse(12345)  # type: ignore
        check("parse invalid type raises TypeError", False)
    except TypeError:
        check("parse invalid type raises TypeError", True)

    # 6. Reference.create()
    created1 = Reference.create("Patient", "pat-1")
    check("create string type", created1 == {"reference": "Patient/pat-1"})

    created2 = Reference.create(Patient, "pat-2", display="Alice")
    check("create class type with display", created2 == {"reference": "Patient/pat-2", "display": "Alice"})

    # 7. to_dict() and repr()
    check("to_dict() matches", ref3.to_dict() == {"reference": "Condition/cond-1", "display": "Hypertension", "type": "Condition"})
    check("repr contains reference", "Condition/cond-1" in repr(ref3))


def test_reference_and_path():
    test_get_path()
    test_reference()
    print("Reference and Path tests passed successfully!")


if __name__ == "__main__":
    test_reference_and_path()
