# FHIR Lite

[![PyPI version](https://img.shields.io/pypi/v/fhir-lite.svg)](https://pypi.org/project/fhir-lite/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-Zero%20(stdlib%20only)-success.svg)]()
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=buhozurdo_fhir-lite&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=buhozurdo_fhir-lite)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=buhozurdo_fhir-lite&metric=coverage)](https://sonarcloud.io/summary/new_code?id=buhozurdo_fhir-lite)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**FHIR Lite** is an ultra-lightweight, zero-dependency Python library designed to parse, modify, validate, and convert medical resources under the **HL7 FHIR (Fast Healthcare Interoperability Resources)** standard.

Built specifically for high-throughput, low-latency, and package-size-critical environments (e.g., AWS Lambda, Google Cloud Run, Cloud Functions, and Apache Beam / Dataflow pipelines), it enables seamless interoperability between modern systems (JSON) and legacy healthcare systems (XML).

---

## ⚡ Performance Benchmark

| Metric | Heavy Conventional Libraries | **FHIR Lite** | Advantage |
| :--- | :---: | :---: | :---: |
| **Import / Cold-Start** | ~350 ms – 600 ms | **$\le$ 2 ms** | **> 150x faster** |
| **Memory Baseline** | ~80 MB – 140 MB | **< 12 MB** | **> 85% RAM savings** |
| **Wheel Package Size** | ~30 MB – 50 MB | **< 100 KB** | **Ultra-lean** |
| **Runtime Dependencies** | 10 – 35 packages | **0 (stdlib only)** | **Zero supply-chain risk** |
| **Bundle (500 entries) Filter** | ~12 ms | **0.4 ms** | **30x throughput** |

*Run benchmarks locally via `python benchmarks/benchmark.py`.*

---

## Features

* **Zero Dependencies:** Relies exclusively on Python's standard library (`json`, `xml.etree.ElementTree`, `urllib`). No supply-chain baggage.
* **Serverless-Friendly:** Sub-millisecond cold start with near-zero memory footprint.
* **Lossless Bidirectional Conversion:** Accurately converts between FHIR JSON and FHIR XML.
* **Native FHIRPath Mini-Engine:** Pure-Python AST parser and evaluator supporting `.where()`, `.exists()`, projections, and comparisons.
* **HIPAA Safe Harbor De-identification:** Built-in sanitization, date-shifting, and salted SHA-256 pseudonymization.
* **High-Throughput Bulk Data (NDJSON):** 64KB bounded I/O streaming with transparent gzip support.
* **Extensible Architecture:** Base `FHIRResource` class with dictionary/attribute access, slotted memory, and custom validation hooks.

---

## Installation

Install the latest release directly from [PyPI](https://pypi.org/project/fhir-lite/):

```bash
pip install fhir-lite
```

Because **FHIR Lite** has zero external dependencies, you can also simply vendor the `fhir_lite` directory into your project, or install locally:

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

# Safe deep path traversal (dot-notation or key sequences)
print(patient.get_path("name.0.family"))               # "Smith"
print(patient.get_path("name.0.given.0"))              # "Jane"
print(patient.get_path("missing.field", default="N/A")) # "N/A"

# Semantic extractors for identifiers and medical codes
print(patient.get_identifier(system="http://hospital.org/mrn")) # "MRN-123"
# print(obs.get_coding(system="http://loinc.org"))               # "883-9"

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
from fhir_lite import FHIRClient, Patient, Bundle

client = FHIRClient(
    base_url="https://hapi.fhir.org/baseR4",
    auth="my-bearer-token",  # or auth=("user", "password")
    max_retries=3,           # Automatic retry on 429 (rate limit), 502, 503, 504
    backoff_factor=0.5,      # Exponential backoff + Retry-After header parsing
)

# Fetch a resource by ID (auto-instantiates typed Patient)
patient = client.read(Patient, "12345")

# Conditional Create (If-None-Exist) & Idempotent get_or_create
patient, created = client.get_or_create(patient, identifier="http://hospital.org/mrn|12345")

# FHIR JSON Patch (partial updates without race conditions)
client.patch(Patient, patient.id, [
    {"op": "replace", "path": "/active", "value": False}
])

# Automatic multi-page search iterator (follows bundle.link 'next')
for pat in client.iter_search(Patient, family="Smith", max_pages=5):
    print(pat.id)

# Fluent Transaction & Batch Builder (POST [base])
tx = Bundle.transaction()
tx.add_create(Patient(gender="female", active=True))
tx.add_delete(Patient, "old-patient-id")
tx_response = client.transaction(tx)
```

---

### 7. Optional Pydantic Interoperability (Soft Dependency)

`fhir-lite` has **zero required dependencies**, but if you or your framework (e.g., FastAPI) uses **Pydantic** (v1 or v2), you can seamlessly convert models back and forth:

```python
from pydantic import BaseModel
from fhir_lite import FHIRResource

class MyPatientModel(BaseModel):
    resourceType: str = "Patient"
    id: str
    active: bool = True
    gender: str

# 1. Convert any Pydantic model into a typed FHIRResource
pyd_patient = MyPatientModel(id="pat-pyd-1", gender="female")
resource = FHIRResource.from_pydantic(pyd_patient)

# Now enjoy all fhir-lite features: lossless XML conversion, validation, NDJSON streaming
xml_data = resource.to_xml()

# 2. Convert a FHIRResource back into your Pydantic model
pyd_again = resource.to_pydantic(MyPatientModel)
```

---

### 8. FHIR Reference Helpers (`Reference`)

Parse and build FHIR reference strings and dictionaries with ease:

```python
from fhir_lite import Reference, Patient

# Parse string, absolute URL, or dictionary
ref = Reference.parse("Patient/12345")
print(ref.resource_type)  # "Patient"
print(ref.id)             # "12345"

# Create valid reference dictionaries
ref_dict = Reference.create(Patient, "12345", display="Jane Doe")
# {"reference": "Patient/12345", "display": "Jane Doe"}
```

---

### 9. Native FHIRPath Queries (`evaluate_fhirpath`)

Evaluate FHIRPath expressions directly without external runtime dependencies:

```python
from fhir_lite import evaluate_fhirpath, Patient

patient = Patient(
    id="pat-01",
    name=[
        {"use": "official", "family": "Smith", "given": ["Alice"]},
        {"use": "nickname", "family": "Smith", "given": ["Ali"]},
    ],
    telecom=[{"system": "email", "value": "alice@hospital.org"}]
)

# Extract family name from official name entry
family = evaluate_fhirpath(patient, "name.where(use = 'official').family")
# ['Smith']

# Direct boolean criteria evaluation
has_email = evaluate_fhirpath(patient, "telecom.where(system = 'email').exists()")
# [True]
```

---

### 10. HIPAA Safe Harbor De-identification (`anonymize`)

Automate de-identification of 18 HIPAA Safe Harbor direct and indirect identifiers:

```python
from fhir_lite import anonymize, DeidConfig, Patient

patient = Patient(
    id="mrn-12345",
    birthDate="1975-08-14",
    name=[{"family": "Johnson", "given": ["Robert"]}],
    telecom=[{"system": "phone", "value": "555-0199"}],
)

config = DeidConfig(
    date_handling="year_only",     # Truncate to year (1975-01-01)
    pseudonymize_id=True,          # Salted SHA-256 identifier replacement
    salt="hospital-secret-salt",
)

sanitized = anonymize(patient, config=config)
print(sanitized.id)                # "anon-e3b0c44298fc"
print(sanitized.data["birthDate"]) # "1975-01-01"
print(sanitized.data.get("telecom")) # None (stripped)
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
python -m tests.test_optimization
python -m tests.test_pydantic_interop
python -m tests.test_reference_and_path
python -m tests.test_advanced_features
```

---

## Project Structure

```text
fhir-lite/
├── fhir_lite/
│   ├── __init__.py       # Public package interface
│   ├── anonymize.py      # HIPAA Safe Harbor de-identification engine
│   ├── cli.py            # Zero-dependency command-line interface tools
│   ├── client.py         # Resilient REST client with exponential backoff & search iterator
│   ├── fhirpath.py       # Pure-Python AST FHIRPath query evaluator
│   ├── ndjson.py         # High-throughput streaming NDJSON Bulk Data reader/writer
│   ├── py.typed          # PEP 561 inline typing marker
│   ├── resources.py      # Slotted resource models (Patient, Observation, Bundle, Reference)
│   ├── serializer.py     # Lossless JSON/XML converter with XXE defense
│   ├── types.py          # TypedDict definitions for static analysis
│   └── version.py        # FHIRVersion (R4, R4B, R5) context declarations
├── benchmarks/
│   └── benchmark.py      # Reproducible latency and throughput benchmark suite
├── examples/
│   ├── bulk_data_etl.py        # O(1) memory NDJSON streaming and de-identification
│   ├── cloud_rest_client.py    # Resilient cloud server interaction
│   └── serverless_function.py  # Sub-millisecond cold start serverless handler
├── tests/                # Comprehensive unit and integration test suite
├── ARCHITECTURE.md       # Technical design and memory layout specification
├── CONTRIBUTING.md       # Development setup and pull request standards
├── SECURITY.md           # Responsible disclosure and security policy
├── pyproject.toml        # PEP 517/621 packaging metadata
└── README.md
```

## License

MIT