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

class Condition(FHIRResource):
    resource_type = "Condition"
    array_fields = {"category", "evidence", "note"}

    def validate(self) -> list[str]:
        errors = super().validate()
        if "clinicalStatus" not in self.data:
            errors.append("Condition requires 'clinicalStatus'")
        return errors

# Usage
cond = Condition(id="c-01", clinicalStatus="active")
print(cond.is_valid)  # True
print(cond.to_xml())
```

---

## Testing

Run the included standalone test suite (no third-party test runners needed):

```bash
python -m tests.test_fhir_lite
```

---

## Project Structure

```text
fhir-lite/
├── fhir_lite/
│   ├── __init__.py       # Public package interface
│   ├── resources.py      # FHIRResource base, Patient, Observation
│   └── serializer.py     # Fast ElementTree/JSON converter
├── tests/
│   └── test_fhir_lite.py # Self-check test suite
└── README.md
```

## License

MIT