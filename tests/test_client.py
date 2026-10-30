import io
import json
import urllib.error
from unittest.mock import patch, MagicMock
from fhir_lite import (
    FHIRClient,
    FHIRError,
    Patient,
    Observation,
    Bundle,
)


def _mock_response(status=200, payload=None, reason="OK"):
    mock = MagicMock()
    mock.status = status
    mock.reason = reason
    raw = json.dumps(payload).encode("utf-8") if payload is not None else b""
    mock.read.return_value = raw
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


def test_fhir_client():
    client = FHIRClient(base_url="https://fhir.example.com/r4", auth="my-secret-token")
    assert client.headers["Authorization"] == "Bearer my-secret-token"
    assert "application/fhir+json" in client.headers["Accept"]

    # 1. Test read()
    mock_patient_payload = {
        "resourceType": "Patient",
        "id": "123",
        "gender": "female",
        "active": True
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_patient_payload)):
        patient = client.read(Patient, "123")
        assert isinstance(patient, Patient)
        assert patient.id == "123"
        assert patient.gender == "female"

    # 2. Test search()
    mock_bundle_payload = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 1,
        "entry": [
            {
                "fullUrl": "https://fhir.example.com/r4/Patient/123",
                "resource": mock_patient_payload
            }
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_bundle_payload)):
        bundle = client.search("Patient", gender="female", _count=10)
        assert isinstance(bundle, Bundle)
        assert bundle.total == 1
        resources = bundle.get_resources()
        assert len(resources) == 1
        assert isinstance(resources[0], Patient)

    # 3. Test create()
    new_obs = Observation(status="final", code={"text": "Pulse"})
    mock_created_payload = {
        "resourceType": "Observation",
        "id": "obs-new-1",
        "status": "final",
        "code": {"text": "Pulse"}
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(201, mock_created_payload)):
        created = client.create(new_obs)
        assert isinstance(created, Observation)
        assert created.id == "obs-new-1"

    # 4. Test update()
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_created_payload)):
        updated = client.update(created)
        assert isinstance(updated, Observation)

    # 5. Test delete()
    with patch("urllib.request.urlopen", return_value=_mock_response(204, None)):
        success = client.delete(Observation, "obs-new-1")
        assert success is True

    # 6. Test HTTP error handling
    http_error = urllib.error.HTTPError(
        url="https://fhir.example.com/r4/Patient/999",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b'{"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"not-found"}]}')
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        try:
            client.read("Patient", "999")
            assert False, "Should have raised FHIRError"
        except FHIRError as err:
            assert err.status_code == 404
            assert err.outcome is not None
            assert err.outcome["resourceType"] == "OperationOutcome"

    print("All FHIRClient tests passed successfully!")


if __name__ == "__main__":
    test_fhir_client()
