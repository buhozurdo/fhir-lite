import sys
from fhir_lite import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
    Practitioner,
    Encounter,
    Condition,
    MedicationRequest,
    Medication,
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
    class CarePlan(FHIRResource):
        resource_type = "CarePlan"
        def validate(self):
            errs = super().validate()
            if "status" not in self.data:
                errs.append("CarePlan requires status")
            return errs

    plan = CarePlan(id="cp1", status="active")
    assert plan.is_valid
    assert plan.to_dict()["status"] == "active"
    plan_xml = plan.to_xml()
    parsed_plan = from_xml(plan_xml)
    assert isinstance(parsed_plan, CarePlan)
    assert parsed_plan.status == "active"

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

    # 6. Core clinical resources: Practitioner, Encounter, Condition
    doc = Practitioner(id="dr-house", gender="male", active=True, name=[{"family": "House", "given": ["Gregory"]}])
    assert doc.is_valid
    assert doc.gender == "male"
    assert doc.name[0]["family"] == "House"
    doc_xml = doc.to_xml()
    parsed_doc = from_xml(doc_xml)
    assert isinstance(parsed_doc, Practitioner)
    assert parsed_doc.id == "dr-house"

    invalid_doc = Practitioner(id="dr-bad", gender="martian")
    assert not invalid_doc.is_valid
    assert any("Invalid gender" in e for e in invalid_doc.validate())

    enc = Encounter(id="enc-01", status="finished", class_={"code": "AMB", "display": "ambulatory"})
    assert enc.is_valid
    assert enc.status == "finished"
    enc_xml = enc.to_xml()
    parsed_enc = from_xml(enc_xml)
    assert isinstance(parsed_enc, Encounter)

    invalid_enc = Encounter(id="enc-bad", status="not-a-status")
    assert not invalid_enc.is_valid

    cond = Condition(id="cond-01", subject={"reference": "Patient/example-1"}, clinicalStatus={"text": "active"})
    assert cond.is_valid
    cond_xml = cond.to_xml()
    parsed_cond = from_xml(cond_xml)
    assert isinstance(parsed_cond, Condition)
    assert parsed_cond.subject["reference"] == "Patient/example-1"

    invalid_cond = Condition(id="cond-no-subject")
    assert not invalid_cond.is_valid
    assert any("requires 'subject'" in e for e in invalid_cond.validate())

    # 7. Medication resources: MedicationRequest & Medication
    med = Medication(id="med-amox", status="active", code={"text": "Amoxicillin 500mg"})
    assert med.is_valid
    assert med.status == "active"
    med_xml = med.to_xml()
    parsed_med = from_xml(med_xml)
    assert isinstance(parsed_med, Medication)
    assert parsed_med.id == "med-amox"

    med_req = MedicationRequest(
        id="mr-01",
        status="active",
        intent="order",
        subject={"reference": "Patient/example-1"},
        medicationReference={"reference": "Medication/med-amox"}
    )
    assert med_req.is_valid
    assert med_req.status == "active"
    assert med_req.intent == "order"
    req_xml = med_req.to_xml()
    parsed_req = from_xml(req_xml)
    assert isinstance(parsed_req, MedicationRequest)
    assert parsed_req.intent == "order"

    invalid_req = MedicationRequest(id="mr-bad", status="bad-status", intent="bad-intent")
    assert not invalid_req.is_valid
    errs = invalid_req.validate()
    assert any("Invalid status" in e for e in errs)
    assert any("Invalid intent" in e for e in errs)
    assert any("requires 'subject'" in e for e in errs)

    # 8. Primitive extensions support (_element in JSON <-> <element value="..."> in XML)
    ext_patient_json = """{
  "resourceType": "Patient",
  "id": "pat-ext",
  "gender": "other",
  "_gender": {
    "extension": [
      {
        "url": "http://example.org/fhir/StructureDefinition/gender-identity",
        "valueString": "non-binary"
      }
    ]
  }
}"""
    ext_xml = json_to_xml(ext_patient_json)
    assert '<gender value="other">' in ext_xml or '<gender value="other" >' in ext_xml
    assert 'url="http://example.org/fhir/StructureDefinition/gender-identity"' in ext_xml
    assert '<valueString value="non-binary"' in ext_xml

    back_json = xml_to_json(ext_xml)
    parsed_ext_pat = from_json(back_json)
    assert parsed_ext_pat.gender == "other"
    assert "_gender" in parsed_ext_pat
    assert parsed_ext_pat["_gender"]["extension"][0]["valueString"] == "non-binary"

    # Also test from_xml directly
    parsed_from_xml = from_xml(ext_xml)
    assert parsed_from_xml.gender == "other"
    assert parsed_from_xml["_gender"]["extension"][0]["valueString"] == "non-binary"

    print("All FHIR Lite self-checks passed successfully!")


if __name__ == "__main__":
    run_tests()
