# FHIR Lite

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(stdlib%20only)-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

**FHIR Lite** is an ultra-lightweight, zero-dependency Python library designed to parse, modify, validate, and convert medical resources under the **HL7 FHIR (Fast Healthcare Interoperability Resources)** standard.

Built specifically for high-throughput, low-latency, and package-size-critical environments (e.g., AWS Lambda, Google Cloud Run, Cloud Functions, and Apache Beam / Dataflow pipelines), it enables seamless interoperability between modern systems (JSON) and legacy healthcare systems (XML).

---

## Features

* **Zero Dependencies:** Relies exclusively on Python's standard library (`json` and `xml.etree.ElementTree`). No `pip install` bloat or supply-chain baggage.
* **Serverless-Friendly:** Weighs only a few kilobytes with near-zero cold-start overhead.
* **Lossless Bidirectional Conversion:** Accurately converts between FHIR JSON and FHIR XML, honoring FHIR namespaces (`http://hl7.org/fhir`), primitive `value` attributes, and list element representations.
* **Extensible Object-Oriented Architecture:** Base `FHIRResource` class with dictionary/attribute access, automatic subclass registration, and custom validation hooks (includes pre-built `Patient` and `Observation`).

---

## Installation

Because **FHIR Lite** has zero external dependencies, you can simply vendor the `fhir_lite` directory into your project, or install locally:

```bash
# Clone the repository
git clone https://github.com/BuhoZurdo/fhir-lite.git

# Or copy `fhir_lite/` directly into your AWS Lambda layer or service package
```

---

## Quick Start

### 1. Direct JSON $\leftrightarrow$ XML Conversion

Transform payloads directly without instantiating resource classes—ideal for proxy microservices, API gateways, and ETL pipelines:

```python
from fhir_lite import json_to_xml, xml_to_json

# Convert FHIR JSON to formatted FHIR XML
fhir_json = '''{
  "resourceType": "Patient",
  "id": "pat-001",
  "active": true,
  "gender": "male"
}'''

xml_output = json_to_xml(fhir_json, pretty=True)
print(xml_output)
# Output:
# <Patient xmlns="http://hl7.org/fhir">
#   <id value="pat-001" />
#   <active value="true" />
#   <gender value="male" />
# </Patient>

# Convert back from XML to JSON
json_output = xml_to_json(xml_output, indent=2)
```

---

### 2. Working with Resources (`Patient`, `Observation`)

Access fields via attributes or dictionary keys with built-in validation:

```python
from fhir_lite import Patient, Observation

# Initialize with keyword arguments or dictionaries
patient = Patient(
    id="pat-100",
    active=True,
    gender="female",
    name=[{"use": "official", "family": "Smith", "given": ["Jane"]}]
)

# Access fields seamlessly
print(patient.id)             # "pat-100"
print(patient["gender"])      # "female"
print(patient.is_valid)       # True

# Export to JSON or XML
print(patient.to_json())
print(patient.to_xml())
```

---

### 3. Dynamic Deserialization (`from_json` / `from_xml`)

The library automatically detects the `resourceType` and instantiates the registered subclass:

```python
from fhir_lite import from_json, from_xml, Patient, Observation

# Automatically instantiates a Patient
res = from_json('{"resourceType": "Patient", "id": "p1", "gender": "male"}')
assert isinstance(res, Patient)

# Automatically instantiates an Observation
xml_data = '<Observation xmlns="http://hl7.org/fhir"><id value="obs-1"/><status value="final"/><code/></Observation>'
obs = from_xml(xml_data)
assert isinstance(obs, Observation)
```

---

### 4. Creating Custom Resources

Inheriting from `FHIRResource` automatically registers the new resource type with the dynamic deserializer and validator:

```python
from fhir_lite import FHIRResource

class CarePlan(FHIRResource):
    resource_type = "CarePlan"
    array_fields = {"category", "activity", "note"}

    def validate(self) -> list[str]:
        errors = super().validate()
        if "status" not in self.data:
            errors.append("CarePlan requires 'status'")
        return errors

# Usage
plan = CarePlan(id="cp-01", status="active")
print(plan.is_valid)  # True
print(plan.to_xml())
```

---

### 5. FHIR Bulk Data (NDJSON Streaming)

Process massive clinical datasets (e.g. from AWS HealthLake, Google Cloud Healthcare, or Athena) line-by-line with $O(1)$ constant memory overhead and transparent `.gz` decompression:

```python
from fhir_lite import iter_ndjson, write_ndjson

# Stream resources from plain or gzipped NDJSON
for resource in iter_ndjson("patients.ndjson.gz"):
    if resource.is_valid:
        print(f"Processed: {resource.resource_type}/{resource.id}")

# Stream write resources to a compressed file
write_ndjson([patient, observation], "export.ndjson.gz")
```

---

### 6. Zero-Dependency REST Client (`FHIRClient`)

Interact with FHIR servers (e.g. HAPI, AWS HealthLake, Google Healthcare) using Python's standard library `urllib` without installing `requests` or `httpx`:

```python
from fhir_lite import FHIRClient, Patient

client = FHIRClient(
    base_url="https://hapi.fhir.org/baseR4",
    auth="my-bearer-token"  # or auth=("user", "password")
)

# Fetch a resource by ID (auto-instantiates typed Patient)
patient = client.read(Patient, "12345")
print(patient.gender)

# Search with parameters (returns typed Bundle)
bundle = client.search(Patient, family="Smith", _count=20)
for pat in bundle.get_resources():
    print(pat.id)

# Create / Update / Delete
new_patient = client.create(Patient(gender="female", active=True))
client.delete(Patient, new_patient.id)
```

---

## Testing

Run the included standalone test suites (no third-party test runners needed):

```bash
python -m tests.test_fhir_lite
python -m tests.test_security
python -m tests.test_ndjson
python -m tests.test_client
python -m tests.test_typing
python -m tests.test_version
python -m tests.test_operation_outcome
```

---

## Project Structure

```text
fhir-lite/
├── fhir_lite/
│   ├── __init__.py       # Public package interface
│   ├── client.py         # Zero-dependency FHIR REST client (urllib) & FHIRError
│   ├── ndjson.py         # Streaming NDJSON Bulk Data reader/writer (gzip support)
│   ├── py.typed          # PEP 561 inline typing marker
│   ├── resources.py      # Core resources (Patient, Observation, Bundle, OperationOutcome, etc.)
│   ├── serializer.py     # Fast ElementTree/JSON converter (XXE/DoS protected, primitive extensions)
│   ├── types.py          # TypedDict definitions for common FHIR structures
│   └── version.py        # FHIRVersion (R4, R4B, R5) declarations and context manager
├── tests/
│   ├── test_client.py            # Mocked FHIR REST client tests
│   ├── test_fhir_lite.py         # Core resource, validation, and extension test suite
│   ├── test_ndjson.py            # Streaming & gzip bulk data tests
│   ├── test_operation_outcome.py # OperationOutcome & error integration tests
│   ├── test_security.py          # XXE, DTD, and parser security tests
│   ├── test_typing.py            # PEP 561 & TypedDict tests
│   └── test_version.py           # FHIR R4/R5 version context & alias tests
├── pyproject.toml        # PEP 517/621 packaging metadata
└── README.md
```

## License

MIT