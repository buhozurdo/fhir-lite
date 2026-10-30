import sys
from fhir_lite import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
    from_json,
    from_xml,
    json_to_xml,
    xml_to_json,
)


def run_tests():
    # 1. Bidirectional JSON <-> XML
    sample_json = """{
  "resourceType": "Patient",
  "id": "example-1",
  "active": true,
  "gender": "male",
  "name": [
    {
      "use": "official",
      "family": "Chalmers",
      "given": [
        "Peter",
        "James"
      ]
    }
  ]
}"""
    xml_out = json_to_xml(sample_json)
    assert "<Patient" in xml_out
    assert 'xmlns="http://hl7.org/fhir"' in xml_out
    assert '<id value="example-1"' in xml_out
    assert '<active value="true"' in xml_out
    assert '<given value="Peter"' in xml_out
    assert '<given value="James"' in xml_out

    json_back = xml_to_json(xml_out)
    res_patient = from_json(json_back)
    assert isinstance(res_patient, Patient)
    assert res_patient.id == "example-1"
    assert res_patient.active is True
    assert res_patient.name[0]["family"] == "Chalmers"
    assert res_patient.name[0]["given"] == ["Peter", "James"]
    assert res_patient.is_valid

    # 2. Patient validation
    invalid_patient = Patient({"resourceType": "Patient", "gender": "non-binary", "active": "yes"})
    errors = invalid_patient.validate()
    assert len(errors) == 2, f"Expected 2 errors, got: {errors}"
    assert not invalid_patient.is_valid

    # 3. Observation validation
    obs = Observation({
        "resourceType": "Observation",
        "id": "obs-1",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]}
    })
    assert obs.is_valid
    xml_obs = obs.to_xml()
    obs_from_xml = from_xml(xml_obs)
    assert isinstance(obs_from_xml, Observation)
    assert obs_from_xml.status == "final"

    # 4. Custom resource subclassing
    class Condition(FHIRResource):
        resource_type = "Condition"
        def validate(self):
            errs = super().validate()
            if "clinicalStatus" not in self.data:
                errs.append("Condition requires clinicalStatus")
            return errs

    cond = Condition(id="c1", clinicalStatus="active")
    assert cond.is_valid
    assert cond.to_dict()["clinicalStatus"] == "active"
    cond_xml = cond.to_xml()
    parsed_cond = from_xml(cond_xml)
    assert isinstance(parsed_cond, Condition)
    assert parsed_cond.clinicalStatus == "active"

    # 5. Bundle support & nested resources
    bundle = Bundle(type="searchset", total=0)
    assert bundle.is_valid

    invalid_bundle = Bundle(type="unknown-type")
    assert not invalid_bundle.is_valid
    assert any("Invalid Bundle type" in e for e in invalid_bundle.validate())

    p = Patient(id="pat-bundle-1", active=True, gender="female")
    o = Observation(id="obs-bundle-1", status="final", code={"text": "Pulse"})
    bundle.add_entry(p, full_url="http://example.org/fhir/Patient/pat-bundle-1")
    bundle.add_entry(o, full_url="http://example.org/fhir/Observation/obs-bundle-1")

    assert len(bundle.entries) == 2
    assert bundle.total == 2

    # Verify resource extraction
    extracted = bundle.get_resources()
    assert len(extracted) == 2
    assert isinstance(extracted[0], Patient)
    assert isinstance(extracted[1], Observation)
    assert extracted[0].id == "pat-bundle-1"
    assert extracted[1].status == "final"

    # Verify filter by type
    patients = bundle.get_resources_by_type("Patient")
    assert len(patients) == 1
    assert patients[0].gender == "female"

    observations = bundle.get_resources_by_type(Observation)
    assert len(observations) == 1
    assert observations[0].id == "obs-bundle-1"

    # Verify XML <-> JSON roundtrip with inner resource elements
    bundle_xml = bundle.to_xml()
    assert "<Bundle" in bundle_xml
    assert "<entry>" in bundle_xml
    assert "<resource>" in bundle_xml
    assert "<Patient>" in bundle_xml
    assert '<id value="pat-bundle-1"' in bundle_xml
    assert "<Observation>" in bundle_xml

    parsed_bundle = from_xml(bundle_xml)
    assert isinstance(parsed_bundle, Bundle)
    assert parsed_bundle.type == "searchset"
    parsed_resources = parsed_bundle.get_resources()
    assert len(parsed_resources) == 2
    assert isinstance(parsed_resources[0], Patient)
    assert parsed_resources[0].id == "pat-bundle-1"
    assert isinstance(parsed_resources[1], Observation)
    assert parsed_resources[1].status == "final"

    print("All FHIR Lite self-checks passed successfully!")


if __name__ == "__main__":
    run_tests()
