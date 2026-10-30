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
    OperationOutcome,
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
from .types import (
    ExtensionDict,
    CodingDict,
    CodeableConceptDict,
    ReferenceDict,
    QuantityDict,
    PeriodDict,
    IdentifierDict,
    HumanNameDict,
    ContactPointDict,
    AddressDict,
    MetaDict,
    BundleEntryDict,
    BundleEntryRequestDict,
    BundleEntryResponseDict,
    DosageDict,
    NarrativeDict,
    IssueDict,
)
from .version import (
    FHIRVersion,
    get_fhir_version,
    set_fhir_version,
    fhir_version_context,
    normalize_field,
    get_version_info,
)


def from_json(json_str: str) -> FHIRResource:
    """Parse a FHIR JSON string into the appropriate FHIRResource instance."""
    return FHIRResource.from_json(json_str)


def from_xml(xml_str: str) -> FHIRResource:
    """Parse a FHIR XML string into the appropriate FHIRResource instance."""
    return FHIRResource.from_xml(xml_str)


__all__ = [
    # Resources
    "FHIRResource",
    "Patient",
    "Observation",
    "Bundle",
    "Practitioner",
    "Encounter",
    "Condition",
    "MedicationRequest",
    "Medication",
    "OperationOutcome",
    # Client
    "FHIRClient",
    "FHIRError",
    # Convenience parsers
    "from_json",
    "from_xml",
    # Serializer
    "json_to_xml",
    "xml_to_json",
    "dict_to_xml",
    "xml_to_dict",
    "safe_fromstring",
    # NDJSON
    "iter_ndjson",
    "write_ndjson",
    "loads_ndjson",
    "dumps_ndjson",
    # TypedDicts (fhir_lite.types)
    "ExtensionDict",
    "CodingDict",
    "CodeableConceptDict",
    "ReferenceDict",
    "QuantityDict",
    "PeriodDict",
    "IdentifierDict",
    "HumanNameDict",
    "ContactPointDict",
    "AddressDict",
    "MetaDict",
    "BundleEntryDict",
    "BundleEntryRequestDict",
    "BundleEntryResponseDict",
    "DosageDict",
    "NarrativeDict",
    "IssueDict",
    # Version API (fhir_lite.version)
    "FHIRVersion",
    "get_fhir_version",
    "set_fhir_version",
    "fhir_version_context",
    "normalize_field",
    "get_version_info",
]
