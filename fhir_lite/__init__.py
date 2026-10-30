"""
FHIR Lite: Ultra-lightweight, zero-dependency FHIR library for Python.
"""

from .serializer import (
    json_to_xml,
    xml_to_json,
    dict_to_xml,
    xml_to_dict,
)
from .resources import (
    FHIRResource,
    Patient,
    Observation,
    Bundle,
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
    "from_json",
    "from_xml",
    "json_to_xml",
    "xml_to_json",
    "dict_to_xml",
    "xml_to_dict",
]
