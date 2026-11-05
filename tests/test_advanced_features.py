"""
Tests for v0.4.0 features solving real-world pain points:
- Semantic extractors: get_identifier, get_coding
- Fluent transaction & batch builders: Bundle.transaction(), Bundle.batch(), add_create(), add_update(), add_delete()
- Retries with exponential backoff & Retry-After handling in FHIRClient
- Conditional create (If-None-Exist) and get_or_create
- FHIR JSON Patch (application/json-patch+json)
"""

import io
import json
import urllib.error
from unittest.mock import patch, MagicMock

from fhir_lite import (
    Patient,
    Observation,
    Bundle,
    FHIRClient,
    FHIRError,
    FHIRResource,
)


def _mock_resp(status=200, payload=None, headers=None):
    mock = MagicMock()
    mock.status = status
    raw = json.dumps(payload).encode("utf-8") if payload is not None else b""
    mock.read.return_value = raw
    mock.headers = headers or {}
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


def test_semantic_extractors():
    print("Testing semantic extractors (get_identifier, get_coding)...")
    pat = Patient(
        id="p1",
        identifier=[
            {"system": "http://hospital.org/mrn", "value": "MRN-12345"},
            {"system": "http://gov.org/ssn", "value": "SSN-99999"},
            {
                "type": {"coding": [{"code": "TAX", "system": "http://hl7.org/fhir/v2/0203"}]},
                "value": "TAX-777",
            },
        ],
    )

    # 1. get_identifier by system
    assert pat.get_identifier(system="http://hospital.org/mrn") == "MRN-12345"
    assert pat.get_identifier(system="http://gov.org/ssn") == "SSN-99999"
    assert pat.get_identifier(system="http://nonexistent.org") is None

    # 2. get_identifier by type_code
    assert pat.get_identifier(type_code="TAX") == "TAX-777"
    assert pat.get_identifier(type_code="NONEXISTENT") is None

    # 3. get_coding from CodeableConcept
    obs = Observation(
        status="final",
        code={
            "coding": [
                {"system": "http://loinc.org", "code": "883-9", "display": "ABO group"},
                {"system": "http://snomed.info/sct", "code": "365636006"},
            ]
        },
        category=[
            {
                "coding": [
                    {"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}
                ]
            }
        ],
    )

    assert obs.get_coding(system="http://loinc.org") == "883-9"
    assert obs.get_coding(system="http://snomed.info/sct") == "365636006"
    assert obs.get_coding(system="http://unknown.org") is None
    # Default without system returns first code
    assert obs.get_coding() == "883-9"

    # get_coding from category list
    assert obs.get_coding(field="category") == "laboratory"


def test_fluent_bundle_builders():
    print("Testing fluent bundle builders (Bundle.transaction, Bundle.batch)...")

    # 1. Bundle.transaction()
    p = Patient(id="pat-1", active=True)
    tx = Bundle.transaction(p)
    assert tx.type == "transaction"
    assert len(tx.entries) == 1
    assert tx.entries[0]["request"]["method"] == "POST"
    assert tx.entries[0]["request"]["url"] == "Patient"

    # 2. add_update()
    obs = Observation(id="obs-1", status="final", code={"text": "Pulse"})
    tx.add_update(obs)
    assert len(tx.entries) == 2
    assert tx.entries[1]["request"]["method"] == "PUT"
    assert tx.entries[1]["request"]["url"] == "Observation/obs-1"

    # 3. add_delete()
    tx.add_delete(Patient, "pat-99")
    assert len(tx.entries) == 3
    assert tx.entries[2]["request"]["method"] == "DELETE"
    assert tx.entries[2]["request"]["url"] == "Patient/pat-99"

    # 4. Bundle.batch()
    batch = Bundle.batch()
    assert batch.type == "batch"
    batch.add_create({"resourceType": "Condition", "subject": {"reference": "Patient/pat-1"}})
    assert len(batch.entries) == 1
    assert batch.entries[0]["request"]["method"] == "POST"
    assert batch.entries[0]["request"]["url"] == "Condition"


def test_conditional_create_and_get_or_create():
    print("Testing conditional create and get_or_create...")
    client = FHIRClient(base_url="https://fhir.example.com/r4")

    pat = Patient(gender="female", identifier=[{"system": "http://hospital.org", "value": "123"}])

    # 1. create with if_none_exist
    captured_req = None

    def mock_open_if_none(req, timeout=30.0):
        nonlocal captured_req
        captured_req = req
        return _mock_resp(201, {"resourceType": "Patient", "id": "created-1", "gender": "female"})

    with patch.object(client, "_open_request", side_effect=mock_open_if_none):
        res = client.create(pat, if_none_exist="identifier=http://hospital.org|123")
        assert res.id == "created-1"
        assert captured_req.headers.get("If-none-exist") == "identifier=http://hospital.org|123"

    # 2. get_or_create: resource created (new id)
    with patch.object(client, "_open_request", return_value=_mock_resp(201, {"resourceType": "Patient", "id": "new-p"})):
        res, created = client.get_or_create(pat, identifier="http://hospital.org|123")
        assert res.id == "new-p"
        assert created is True

    # 3. get_or_create: resource already exists (same id returned)
    pat_existing = Patient(id="existing-1", gender="male")
    with patch.object(client, "_open_request", return_value=_mock_resp(200, {"resourceType": "Patient", "id": "existing-1"})):
        res, created = client.get_or_create(pat_existing, identifier="http://hospital.org|999")
        assert res.id == "existing-1"
        assert created is False


def test_fhir_json_patch():
    print("Testing FHIR JSON Patch (client.patch)...")
    client = FHIRClient(base_url="https://fhir.example.com/r4")

    patch_ops = [
        {"op": "replace", "path": "/active", "value": False},
        {"op": "add", "path": "/telecom/-", "value": {"system": "email", "value": "jane@example.com"}},
    ]

    captured_req = None

    def mock_open_patch(req, timeout=30.0):
        nonlocal captured_req
        captured_req = req
        return _mock_resp(200, {"resourceType": "Patient", "id": "pat-10", "active": False})

    with patch.object(client, "_open_request", side_effect=mock_open_patch):
        patched = client.patch(Patient, "pat-10", patch_ops)
        assert patched.id == "pat-10"
        assert patched.active is False
        assert captured_req.get_method() == "PATCH"
        assert captured_req.headers.get("Content-type") == "application/json-patch+json"


def test_client_retries_and_backoff():
    print("Testing client retries with backoff and Retry-After...")
    client = FHIRClient(
        base_url="https://fhir.example.com/r4",
        max_retries=2,
        backoff_factor=0.01,  # Fast backoff for tests
    )

    # 1. Retry on 429 then succeed
    attempts = 0

    def mock_429_then_200(req, timeout=30.0):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            hdrs = {"Retry-After": "0.01"}
            err = urllib.error.HTTPError(
                url=req.full_url,
                code=429,
                msg="Too Many Requests",
                hdrs=hdrs,
                fp=io.BytesIO(b'{"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"throttled"}]}'),
            )
            err.headers = hdrs
            raise err
        return _mock_resp(200, {"resourceType": "Patient", "id": "p-recovered"})

    with patch.object(client, "_open_request", side_effect=mock_429_then_200):
        p = client.read(Patient, "123")
        assert p.id == "p-recovered"
        assert attempts == 2

    # 2. Exceed max_retries and raise FHIRError
    attempts = 0

    def mock_always_503(req, timeout=30.0):
        nonlocal attempts
        attempts += 1
        err = urllib.error.HTTPError(
            url=req.full_url,
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"transient"}]}'),
        )
        raise err

    with patch.object(client, "_open_request", side_effect=mock_always_503):
        try:
            client.read(Patient, "123")
            raise AssertionError("Should have raised FHIRError after retries exhausted")
        except FHIRError as err:
            assert err.status_code == 503
            assert attempts == 3  # initial + 2 retries


def test_all_advanced_features():
    test_semantic_extractors()
    test_fluent_bundle_builders()
    test_conditional_create_and_get_or_create()
    test_fhir_json_patch()
    test_client_retries_and_backoff()
    print("All advanced feature tests passed successfully!")


if __name__ == "__main__":
    test_all_advanced_features()
