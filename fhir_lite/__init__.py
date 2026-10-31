"""
FHIR Lite: Ultra-lightweight, zero-dependency FHIR library for Python.

Uses PEP 562 lazy module loading to ensure sub-millisecond cold starts
and minimal baseline memory footprint in serverless environments.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

__version__ = "0.1.0"

# Mapping from public symbols to their internal modules for lazy loading
_SUBMODULE_MAP = {
    # Resources
    "FHIRResource": ".resources",
    "Patient": ".resources",
    "Observation": ".resources",
    "Bundle": ".resources",
    "Practitioner": ".resources",
    "Encounter": ".resources",
    "Condition": ".resources",
    "MedicationRequest": ".resources",
    "Medication": ".resources",
    "OperationOutcome": ".resources",
    # Client
    "FHIRClient": ".client",
    "FHIRError": ".client",
    # Serializer
    "json_to_xml": ".serializer",
    "xml_to_json": ".serializer",
    "dict_to_xml": ".serializer",
    "xml_to_dict": ".serializer",
    "safe_fromstring": ".serializer",
    # NDJSON
    "iter_ndjson": ".ndjson",
    "write_ndjson": ".ndjson",
    "loads_ndjson": ".ndjson",
    "dumps_ndjson": ".ndjson",
    # TypedDicts (fhir_lite.types)
    "ExtensionDict": ".types",
    "CodingDict": ".types",
    "CodeableConceptDict": ".types",
    "ReferenceDict": ".types",
    "QuantityDict": ".types",
    "PeriodDict": ".types",
    "IdentifierDict": ".types",
    "HumanNameDict": ".types",
    "ContactPointDict": ".types",
    "AddressDict": ".types",
    "MetaDict": ".types",
    "BundleEntryDict": ".types",
    "BundleEntryRequestDict": ".types",
    "BundleEntryResponseDict": ".types",
    "DosageDict": ".types",
    "NarrativeDict": ".types",
    "IssueDict": ".types",
    # Version API (fhir_lite.version)
    "FHIRVersion": ".version",
    "get_fhir_version": ".version",
    "set_fhir_version": ".version",
    "fhir_version_context": ".version",
    "normalize_field": ".version",
    "get_version_info": ".version",
}


def from_json(json_str: str):
    """Parse a FHIR JSON string into the appropriate FHIRResource instance."""
    from .resources import FHIRResource
    return FHIRResource.from_json(json_str)


def from_xml(xml_str: str):
    """Parse a FHIR XML string into the appropriate FHIRResource instance."""
    from .resources import FHIRResource
    return FHIRResource.from_xml(xml_str)


def __getattr__(name: str):
    """PEP 562 lazy loading: imports submodules on-demand when accessed."""
    submodule = _SUBMODULE_MAP.get(name)
    if submodule is not None:
        mod = importlib.import_module(submodule, __package__)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return __all__


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


if TYPE_CHECKING:
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
    from .client import (
        FHIRClient,
        FHIRError,
    )
    from .serializer import (
        json_to_xml,
        xml_to_json,
        dict_to_xml,
        xml_to_dict,
        safe_fromstring,
    )
    from .ndjson import (
        iter_ndjson,
        write_ndjson,
        loads_ndjson,
        dumps_ndjson,
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
