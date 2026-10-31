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
            raise AssertionError("Should have raised FHIRError")
        except FHIRError as err:
            assert err.status_code == 404
            assert err.outcome is not None
            assert err.outcome["resourceType"] == "OperationOutcome"

    # 7. Test Bundle link parsing (next_url, prev_url, get_link)
    b_links = Bundle(
        type="searchset",
        link=[
            {"relation": "self", "url": "https://fhir.example.com/r4/Patient?_count=1"},
            {"relation": "next", "url": "https://fhir.example.com/r4/Patient?_count=1&page=2"},
            {"relation": "previous", "url": "https://fhir.example.com/r4/Patient?_count=1&page=0"},
        ]
    )
    assert b_links.next_url == "https://fhir.example.com/r4/Patient?_count=1&page=2"
    assert b_links.prev_url == "https://fhir.example.com/r4/Patient?_count=1&page=0"
    assert b_links.get_link("self") == "https://fhir.example.com/r4/Patient?_count=1"
    assert b_links.get_link("nonexistent") is None

    b_prev_alias = Bundle(type="searchset", link=[{"relation": "prev", "url": "https://fhir.example.com/prev"}])
    assert b_prev_alias.prev_url == "https://fhir.example.com/prev"

    b_no_links = Bundle(type="searchset")
    assert b_no_links.next_url is None
    assert b_no_links.prev_url is None
    assert client.next_page(b_no_links) is None
    assert client.prev_page(b_no_links) is None

    # 8. Test next_page and prev_page network calls
    mock_page2_payload = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p-page-2", "gender": "male"}}
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_page2_payload)):
        page2 = client.next_page(b_links)
        assert page2 is not None
        assert page2.type == "searchset"
        resources = page2.get_resources()
        assert len(resources) == 1
        assert resources[0].id == "p-page-2"

        page_prev = client.prev_page(b_links)
        assert page_prev is not None
        assert len(page_prev.get_resources()) == 1

    # 9. Test iter_search() across multiple pages
    page1_payload = {
        "resourceType": "Bundle",
        "type": "searchset",
        "link": [{"relation": "next", "url": "https://fhir.example.com/r4/Patient?page=2"}],
        "entry": [{"resource": {"resourceType": "Patient", "id": "p-1", "gender": "male"}}]
    }
    page2_payload = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": {"resourceType": "Patient", "id": "p-2", "gender": "female"}}]
    }

    call_count = 0
    def mock_urlopen_multipage(req, timeout=30.0):
        nonlocal call_count
        call_count += 1
        if "page=2" in req.full_url:
            return _mock_response(200, page2_payload)
        return _mock_response(200, page1_payload)

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_multipage):
        all_patients = list(client.iter_search(Patient, gender="male"))
        assert len(all_patients) == 2
        assert [p.id for p in all_patients] == ["p-1", "p-2"]

    # Test iter_search() with max_pages=1
    with patch("urllib.request.urlopen", side_effect=mock_urlopen_multipage):
        limited_patients = list(client.iter_search(Patient, max_pages=1))
        assert len(limited_patients) == 1
        assert limited_patients[0].id == "p-1"

    # 10. Test transaction() and batch()
    tx_bundle = Bundle(type="transaction")
    tx_bundle.add_entry(resource=Patient(id="pat-tx", gender="male"), request={"method": "POST", "url": "Patient"})
    mock_tx_resp = {
        "resourceType": "Bundle",
        "type": "transaction-response",
        "entry": [{"response": {"status": "201 Created", "location": "Patient/pat-tx/_history/1"}}]
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_tx_resp)) as mock_call:
        res = client.transaction(tx_bundle)
        assert res.type == "transaction-response"
        assert len(res.entries) == 1

    batch_bundle = Bundle(type="batch")
    batch_bundle.add_entry(request={"method": "GET", "url": "Patient/123"})
    mock_batch_resp = {
        "resourceType": "Bundle",
        "type": "batch-response",
        "entry": [{"response": {"status": "200 OK"}, "resource": {"resourceType": "Patient", "id": "123"}}]
    }
    with patch("urllib.request.urlopen", return_value=_mock_response(200, mock_batch_resp)):
        res = client.batch(batch_bundle)
        assert res.type == "batch-response"

    # Test invalid bundle type check
    try:
        client.transaction(Bundle(type="batch"))
        raise AssertionError("Should have raised ValueError on mismatched type")
    except ValueError as err:
        assert "transaction" in str(err)

    # 11. Test ssl_context and proxy configuration
    import ssl
    dummy_ctx = ssl.create_default_context()
    client_ssl = FHIRClient(base_url="https://fhir.example.com", ssl_context=dummy_ctx)
    assert client_ssl.ssl_context is dummy_ctx
    assert client_ssl._opener is not None

    client_proxy = FHIRClient(base_url="https://fhir.example.com", proxy="http://proxy.hospital.org:8080")
    assert client_proxy.proxy == "http://proxy.hospital.org:8080"
    assert client_proxy._opener is not None

    # Test open_request with mocked opener
    with patch.object(client_ssl._opener, "open", return_value=_mock_response(200, mock_patient_payload)):
        pat = client_ssl.read(Patient, "123")
        assert pat.id == "123"

    print("All FHIRClient tests passed successfully!")


if __name__ == "__main__":
    test_fhir_client()
