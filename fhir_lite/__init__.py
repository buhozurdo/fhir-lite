"""
FHIR Lite: Ultra-lightweight, zero-dependency FHIR library for Python.
"""

__version__ = "0.1.0"

from .serializer import (
    json_to_xml,
    xml_to_json,
    dict_to_xml,
    xml_to_dict,
    safe_fromstring,
)
from .resources import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
    Practitioner,
    Encounter,
    Condition,
    MedicationRequest,
    Medication,
)
from .ndjson import (
    iter_ndjson,
    write_ndjson,
    loads_ndjson,
    dumps_ndjson,
)
from .client import (
    FHIRClient,
    FHIRError,
)


def from_json(json_str: str) -> FHIRResource:
    """Parse a FHIR JSON string into the appropriate FHIRResource instance."""
    return FHIRResource.from_json(json_str)


def from_xml(xml_str: str) -> FHIRResource:
    """Parse a FHIR XML string into the appropriate FHIRResource instance."""
    return FHIRResource.from_xml(xml_str)


__all__ = [
    "FHIRResource",
    "Patient",
    "Observation",
    "Bundle",
    "Practitioner",
    "Encounter",
    "Condition",
    "MedicationRequest",
    "Medication",
    "FHIRClient",
    "FHIRError",
    "from_json",
    "from_xml",
    "json_to_xml",
    "xml_to_json",
    "dict_to_xml",
    "xml_to_dict",
    "safe_fromstring",
    "iter_ndjson",
    "write_ndjson",
    "loads_ndjson",
    "dumps_ndjson",
]
