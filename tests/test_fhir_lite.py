import sys
from fhir_lite import (
    FHIRResource,
    Patient,
    Observation,
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

    print("All FHIR Lite self-checks passed successfully!")


if __name__ == "__main__":
    run_tests()
