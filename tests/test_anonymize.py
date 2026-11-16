"""Tests for TASK-025: HIPAA Safe Harbor De-identification & Sanitization.
"""

import json
import os
import tempfile
from fhir_lite import (
    Patient,
    Observation,
    Bundle,
    anonymize,
    DeidConfig,
)
from fhir_lite.cli import main


def test_default_safe_harbor_patient():
    patient = Patient(
        id="orig-pat-123",
        active=True,
        gender="female",
        name=[
            {"use": "official", "family": "Johnson", "given": ["Sarah", "Ann"]},
            {"use": "maiden", "family": "Miller"},
        ],
        telecom=[
            {"system": "phone", "value": "555-0199", "use": "home"},
            {"system": "email", "value": "sarah.j@example.com"},
        ],
        address=[
            {
                "use": "home",
                "line": ["123 Elm Street", "Apt 4B"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62701",
                "country": "USA",
            }
        ],
        identifier=[
            {"system": "http://hl7.org/fhir/sid/us-ssn", "value": "000-12-3456"},
            {"type": {"coding": [{"code": "MR"}]}, "value": "MRN-998877"},
        ],
        photo=[{"contentType": "image/jpeg", "data": "base64data..."}],
        text={"status": "generated", "div": "<div>Patient Sarah Johnson notes...</div>"},
        birthDate="1984-07-22",
    )

    anon_patient = anonymize(patient)

    # 1. Names replaced with anonymous placeholder
    assert anon_patient.data.get("name") == [{"use": "anonymous", "family": "ANONYMOUS"}]

    # 2. Telecom removed
    assert "telecom" not in anon_patient.data

    # 3. Addresses removed
    assert "address" not in anon_patient.data

    # 4. Identifiers removed
    assert "identifier" not in anon_patient.data

    # 5. Photos removed
    assert "photo" not in anon_patient.data

    # 6. Free-text narrative removed
    assert "text" not in anon_patient.data

    # 7. Date truncated to year only (Safe Harbor)
    assert anon_patient.data.get("birthDate") == "1984-01-01"

    # 8. Clinical characteristics preserved
    assert anon_patient.data.get("gender") == "female"
    assert anon_patient.data.get("active") is True
    assert anon_patient.data.get("id") == "orig-pat-123"


def test_name_placeholder_none():
    patient = Patient(
        name=[{"family": "Smith", "given": ["John"]}],
        gender="male",
    )
    anon = anonymize(patient, config=DeidConfig(name_placeholder=None))
    assert "name" not in anon.data


def test_keep_state_and_country():
    patient = Patient(
        address=[
            {
                "line": ["742 Evergreen Terrace"],
                "city": "Springfield",
                "state": "OR",
                "postalCode": "97477",
                "country": "USA",
            }
        ]
    )
    anon = anonymize(patient, config=DeidConfig(keep_state_and_country=True))
    assert "address" in anon.data
    addr = anon.data["address"][0]
    assert addr.get("state") == "OR"
    assert addr.get("country") == "USA"
    assert "line" not in addr
    assert "city" not in addr
    assert "postalCode" not in addr


def test_date_handling_modes():
    obs = Observation(
        status="final",
        effectiveDateTime="2021-03-10T14:30:00Z",
        issued="2021-03-10T15:00:00Z",
    )

    # 1. Shift dates (+14 days)
    anon_shifted = anonymize(
        obs,
        config=DeidConfig(date_handling="shift", date_shift_days=14),
    )
    assert anon_shifted.data["effectiveDateTime"] == "2021-03-24T14:30:00Z"
    assert anon_shifted.data["issued"] == "2021-03-24T15:00:00Z"

    # 2. Remove dates
    anon_removed = anonymize(
        obs,
        config=DeidConfig(date_handling="remove"),
    )
    assert "effectiveDateTime" not in anon_removed.data
    assert "issued" not in anon_removed.data

    # 3. Preserve dates
    anon_preserved = anonymize(
        obs,
        config=DeidConfig(date_handling="preserve"),
    )
    assert anon_preserved.data["effectiveDateTime"] == "2021-03-10T14:30:00Z"


def test_pseudonymize_id():
    patient = Patient(id="real-id-999", gender="other")
    config = DeidConfig(pseudonymize_id=True, salt="secret-salt-123")

    anon1 = anonymize(patient, config=config)
    anon2 = anonymize(patient, config=config)

    assert anon1.data["id"].startswith("anon-")
    # Deterministic with same salt
    assert anon1.data["id"] == anon2.data["id"]


def test_bundle_anonymization_and_reference_relinking():
    bundle = Bundle(
        type="collection",
        entry=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pat-original-42",
                    "name": [{"family": "Skywalker"}],
                    "birthDate": "1977-05-25",
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-original-1",
                    "status": "final",
                    "subject": {"reference": "Patient/pat-original-42"},
                    "effectiveDateTime": "2022-01-01T10:00:00Z",
                }
            },
        ],
    )

    config = DeidConfig(pseudonymize_id=True, salt="test-salt")
    anon_bundle = anonymize(bundle, config=config)

    entries = anon_bundle.data["entry"]
    anon_pat = entries[0]["resource"]
    anon_obs = entries[1]["resource"]

    # Patient ID pseudonymized
    new_pat_id = anon_pat["id"]
    assert new_pat_id.startswith("anon-")
    assert new_pat_id != "pat-original-42"
    assert anon_pat["name"] == [{"use": "anonymous", "family": "ANONYMOUS"}]

    # Observation reference automatically updated to match new patient ID!
    assert anon_obs["subject"]["reference"] == f"Patient/{new_pat_id}"


def test_resource_anonymize_method_in_place():
    patient = Patient(
        id="p1",
        name=[{"family": "Tesla"}],
        telecom=[{"value": "123-456"}],
    )

    # In place
    ret = patient.anonymize(in_place=True)
    assert ret is patient
    assert "telecom" not in patient.data
    assert patient.data["name"] == [{"use": "anonymous", "family": "ANONYMOUS"}]


def test_cli_anonymize_file_and_piping(monkeypatch, capsys):
    patient_json = json.dumps({
        "resourceType": "Patient",
        "id": "cli-pat-deid",
        "name": [{"family": "Darwin"}],
        "telecom": [{"system": "email", "value": "charles@hmsbeagle.org"}],
        "birthDate": "1809-02-12",
    })

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write(patient_json)
        in_path = in_f.name

    with tempfile.NamedTemporaryFile("r+", delete=False, suffix=".json") as out_f:
        out_path = out_f.name

    try:
        # CLI file conversion
        code = main(["anonymize", in_path, "-o", out_path])
        assert code == 0

        with open(out_path, "r", encoding="utf-8") as f:
            anon_data = json.load(f)

        assert anon_data.get("name") == [{"use": "anonymous", "family": "ANONYMOUS"}]
        assert "telecom" not in anon_data
        assert anon_data.get("birthDate") == "1809-01-01"
    finally:
        os.unlink(in_path)
        os.unlink(out_path)

    # CLI stdin/stdout piping with flag --date-handling shift
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(patient_json))
    code_pipe = main(["anonymize", "--date-handling", "shift", "--date-shift-days", "10"])
    captured = capsys.readouterr()
    assert code_pipe == 0
    parsed = json.loads(captured.out.strip())
    assert parsed.get("birthDate") == "1809-02-22"
    assert "telecom" not in parsed
